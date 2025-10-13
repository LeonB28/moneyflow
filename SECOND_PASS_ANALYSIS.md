# Second Pass: Deep Code Quality Analysis

**Date**: October 13, 2025
**Focus**: Find remaining duplication, coupling issues, missing type hints, test coverage gaps

## Critical Issues Found

### 1. state.py: Unhealthy Coupling & Duplication

#### Issue 1.1: Date Calculations in set_timeframe() (Lines 177-199)
**Problem**: Duplicates TimeNavigator logic!

```python
# THIS_MONTH calculation duplicates TimeNavigator.get_current_month_range()
elif timeframe == TimeFrame.THIS_MONTH:
    today = date.today()
    self.start_date = date(today.year, today.month, 1)
    # Fragile date math for last day of month
    if today.month == 12:
        self.end_date = date(today.year, 12, 31)
    else:
        next_month = date(today.year, today.month + 1, 1)
        from datetime import timedelta
        self.end_date = next_month - timedelta(days=1)
```

**Solution**: Use TimeNavigator
```python
elif timeframe == TimeFrame.THIS_MONTH:
    date_range = TimeNavigator.get_current_month_range()
    self.start_date = date_range.start_date
    self.end_date = date_range.end_date
```

**Benefit**:
- Eliminates date math duplication
- Reuses tested code
- Consistent with other time calculations

#### Issue 1.2: Filtering Logic in get_filtered_df() (Lines 256-294)
**Problem**: Business logic mixed in state object

**Current**: State object has DataFrame filtering logic (search, transfers, hidden)
**Should**: This belongs in data_manager or a separate FilterService

**Coupling Issue**: State shouldn't know about Polars operations

#### Issue 1.3: Breadcrumb Display Logic (Lines 369-421)
**Problem**: 53 lines of display logic in state class!

**Current**: get_breadcrumb() contains string formatting, if/elif chains
**Should**: Extract to ViewPresenter or separate BreadcrumbFormatter

**Test Coverage**: 0% (it's in state.py which has 85% coverage but this method is untested)

#### Issue 1.4: Missing Type Hints
- Line 68: `categories: Dict[str, Any]` - should be `Dict[str, dict]` or TypedDict
- Line 98: `pending_edits: List[TransactionEdit]` - good!
- Line 351: `save_view_state()` returns `dict` - should be TypedDict

### 2. data_manager.py: Code Duplication in Aggregation

#### Issue 2.1: Four Nearly Identical Aggregation Methods (Lines 332-382)

```python
def aggregate_by_merchant(self, df):
    if df.is_empty(): return pl.DataFrame()
    return df.group_by("merchant").agg([pl.count("id").alias("count"), ...])

def aggregate_by_category(self, df):
    if df.is_empty(): return pl.DataFrame()
    return df.group_by("category").agg([pl.count("id").alias("count"), ...])

def aggregate_by_group(self, df):
    if df.is_empty(): return pl.DataFrame()
    return df.group_by("group").agg([pl.count("id").alias("count"), ...])

def aggregate_by_account(self, df):
    if df.is_empty(): return pl.DataFrame()
    return df.group_by("account").agg([pl.count("id").alias("count"), ...])
```

**Duplication**: 51 lines that could be 12 lines

**Solution**: Create generic aggregation function
```python
def aggregate_by_field(
    self,
    df: pl.DataFrame,
    field: str,
    include_ids: bool = True
) -> pl.DataFrame:
    """Generic aggregation by any field."""
    if df.is_empty():
        return pl.DataFrame()

    agg_exprs = [
        pl.count("id").alias("count"),
        pl.sum("amount").alias("total"),
    ]

    if include_ids:
        agg_exprs.append(pl.first(f"{field}_id").alias(f"{field}_id"))

    return df.group_by(field).agg(agg_exprs)

# Then:
def aggregate_by_merchant(self, df):
    return self.aggregate_by_field(df, "merchant")
```

#### Issue 2.2: Four One-Line Filter Methods (Lines 384-398)
**Duplication**: Unnecessary wrapper methods

```python
def filter_by_merchant(self, df, merchant):
    return df.filter(pl.col("merchant") == merchant)

def filter_by_category(self, df, category):
    return df.filter(pl.col("category") == category)

def filter_by_group(self, df, group):
    return df.filter(pl.col("group") == group)

def filter_by_account(self, df, account):
    return df.filter(pl.col("account") == account)
```

**Solution**: Single generic method or just use Polars directly in caller
```python
def filter_by_field(self, df: pl.DataFrame, field: str, value: str) -> pl.DataFrame:
    return df.filter(pl.col(field) == value)
```

**Or**: Remove entirely and use `df.filter(pl.col(field) == value)` in app.py

#### Issue 2.3: Missing Type Hints
- Line 137: `progress_callback: Optional[callable]` - should be `Optional[Callable[[str], None]]`
- Line 194: Same issue
- Line 68-71: `Dict[str, Any]` should be more specific

### 3. screens/edit_screens.py: Merchant Filtering Logic

#### Issue 3.1: Fuzzy Matching Logic in UI (Lines 139-157)
**Problem**: Business logic in screen class

```python
async def _update_suggestions(self, query: str) -> None:
    # Filter merchants
    if query and query != self.current_merchant.lower():
        matches = [
            m for m in self.all_merchants
            if m and query in m.lower() and m != self.current_merchant
        ]
    else:
        matches = [m for m in self.all_merchants if m and m != self.current_merchant]

    # Show top 20 matches
    for merchant in sorted(set(matches))[:20]:
        option_list.add_option(Option(merchant, id=merchant))
```

**Should**: Extract to a MerchantSuggestionService or similar

```python
class MerchantSuggestionService:
    @staticmethod
    def filter_merchants(
        all_merchants: list[str],
        query: str,
        current_merchant: str,
        limit: int = 20
    ) -> list[str]:
        """Filter and rank merchant suggestions."""
        # Testable business logic here
```

#### Issue 3.2: Category Filtering Logic (Lines 279-305)
**Same problem**: Category search/filter logic in UI

Should extract to CategorySearchService with tests for:
- Fuzzy matching
- Case-insensitive search
- Sorting by relevance
- Limit handling

### 4. Missing Type Hints Across Codebase

#### Files with `callable` instead of `Callable`:
- data_manager.py line 137, 194

#### Files with `dict` instead of TypedDict:
- edit_screens.py line 73, 243
- state.py line 351
- many screen classes

#### Files with `list` instead of `list[Type]`:
- edit_screens.py line 72

### 5. Test Coverage Gaps

#### Untested Business Logic:
1. **state.py:set_timeframe()** - Lines 170-199 (date calculations) - **0% coverage**
2. **state.py:get_breadcrumb()** - Lines 369-421 (display logic) - **0% coverage**
3. **state.py:get_filtered_df()** - Lines 256-294 (filtering) - **PARTIALLY tested via integration**
4. **data_manager.py:_build_category_group_mapping()** - Lines 127-131 - **Coverage unclear**
5. **edit_screens:_update_suggestions()** - Lines 134-157 (filtering) - **0% coverage**

#### High-Risk Untested Areas:
- **commit_pending_edits()** in data_manager - async batch commit logic
- **search_transactions()** - search query parsing
- Category filtering in SelectCategoryScreen

### 6. Code Duplication Patterns

#### Pattern 1: Empty DataFrame Checks (5x)
```python
if df.is_empty():
    return pl.DataFrame()
```
Repeated in all aggregation methods.

#### Pattern 2: Filter by Field (4x)
```python
df.filter(pl.col(field) == value)
```
Four nearly identical one-liners.

#### Pattern 3: Transaction Details Formatting (2x)
In EditMerchantScreen and SelectCategoryScreen:
```python
details_text = (
    f"Transaction: {self.transaction_details.get('date', 'N/A')} | "
    f"${self.transaction_details.get('amount', 0):,.2f} | "
    ...
)
```

**Solution**: Create TransactionFormatter utility

### 7. Unhealthy Coupling Patterns

#### Coupling 7.1: State has DataFrame Operations
**Problem**: state.py imports and uses `polars`
**Why Bad**: State should be data, not operations
**Solution**: Move get_filtered_df() to DataManager or FilterService

#### Coupling 7.2: Screens Have Business Logic
**Problem**: edit_screens.py has filtering, sorting, matching logic
**Why Bad**: Can't unit test this logic
**Solution**: Extract to service classes

#### Coupling 7.3: DataManager Has Presentation Concerns
**Problem**: Methods return formatted strings in get_stats()
**Actually**: Not too bad, but could move formatting to ViewPresenter

## Recommended Fixes (Priority Order)

### High Priority (Do Now)

**1. Fix state.py::set_timeframe() to use TimeNavigator**
- Risk: LOW
- Effort: 5 minutes
- Benefit: Eliminates date math duplication, uses tested code

**2. Add missing type hints in data_manager.py**
- Risk: NONE
- Effort: 10 minutes
- Benefit: Type safety, catches bugs

**3. Extract filtering logic from state.get_filtered_df()**
- Risk: MEDIUM
- Effort: 30 minutes
- Benefit: Testable filtering, clearer separation

### Medium Priority (Should Do)

**4. Consolidate aggregation methods in data_manager**
- Risk: LOW
- Effort: 20 minutes
- Benefit: Eliminates 40 lines of duplication

**5. Add type hints to screen classes**
- Risk: NONE
- Effort: 15 minutes
- Benefit: Better IDE support, type safety

**6. Extract merchant/category suggestion logic**
- Risk: MEDIUM
- Effort: 45 minutes
- Benefit: Testable search/filter logic

### Low Priority (Nice to Have)

**7. Extract breadcrumb formatting from state.py**
- Risk: LOW
- Effort: 30 minutes
- Benefit: Cleaner state class

**8. Remove trivial filter_by_* wrappers**
- Risk: MEDIUM (touches many call sites)
- Effort: 20 minutes
- Benefit: Less indirection

## Test Coverage Opportunities

### Easy Wins (Pure Functions):
1. Test set_timeframe() after refactoring
2. Test breadcrumb generation (once extracted)
3. Test merchant suggestion filtering (once extracted)
4. Test category search logic (once extracted)

### Harder (Async/Integration):
1. commit_pending_edits() - need to mock backend
2. fetch_all_data() - partially tested already

## Impact Analysis

### If All High Priority Fixes Done:
- Additional lines saved: ~50
- New tests: ~30
- Coverage increase: +2-3%
- Type safety: Complete for business logic
- Risk: LOW (all changes to pure functions)

### Total if All Fixes Done:
- Additional lines saved: ~100
- New tests: ~60
- Coverage increase: +5%
- All business logic 100% typed
- Clear architectural boundaries

## Recommendations

I recommend proceeding with **High Priority fixes only**:
1. Fix state.set_timeframe() (5 min)
2. Add type hints (10 min)
3. Extract filtering logic (30 min)

**Total time**: ~45 minutes
**Risk**: LOW
**Benefit**: HIGH (eliminates duplication, improves testability)

**Skip** low priority items for now - diminishing returns.

What would you like me to tackle?
