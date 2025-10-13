# Architectural Refactoring Analysis

**Date**: 2025-10-13
**Focus**: Decoupling business logic from UI, eliminating code duplication, improving testability

## Executive Summary

The moneyflow codebase has ~2000 lines in app.py with significant business logic tightly coupled to UI components. This analysis identifies:

1. **Business logic mixed with UI rendering** in app.py
2. **Code duplication** across aggregation views (merchant/category/group/account)
3. **Untestable logic** in UI components
4. **Opportunities for clean separation** into view models and controllers

## Current Architecture Issues

### 1. Business Logic in app.py (Lines 563-835)

**Problem**: Four nearly identical aggregation methods with duplicated sorting/filtering logic:
- `show_merchant_aggregation()` - 50 lines
- `show_category_aggregation()` - 47 lines
- `show_group_aggregation()` - 48 lines
- `show_account_aggregation()` - 47 lines

**Code Duplication Pattern**:
```python
# Repeated in all 4 methods:
1. Add sort arrows to column headers (8 lines)
2. Get filtered data (3 lines)
3. Aggregate by field (1 line)
4. Check if empty (4 lines)
5. Apply sorting with amount inversion (10 lines)
6. Store in state (1 line)
7. Add rows to table (5 lines)
```

**Total duplication**: ~190 lines that should be ~50 lines

### 2. Transaction Display Logic (Lines 754-836)

**Problem**: Business logic for sorting, filtering, and flag computation mixed with UI rendering

**Extractable Logic**:
- Sort field determination and direction inversion
- Transaction filtering by merchant/category/group/account
- Flag computation (✓ H *)
- Cursor position management

### 3. Time Navigation Logic (Lines 968-1121)

**Problem**: Date calculation logic embedded in action methods

**Issues**:
- Month/year math scattered across multiple methods
- `_select_month()`, `action_prev_period()`, `action_next_period()` have date logic
- No tests for edge cases (year boundaries, leap years, etc.)

### 4. Edit Operations (Lines 1247-1631)

**Problem**: Complex edit workflows with business rules in UI layer

**Extractable Logic**:
- Bulk vs single edit determination
- Transaction edit queuing
- Cursor position management
- Edit validation

### 5. Commit Logic (Lines 1677-1827)

**Problem**: DataFrame updates, retry logic, cache management in UI layer

**Critical Issues**:
- DataFrame mutation logic (lines 1726-1797) - 70+ lines of Polars operations
- Retry strategy (lines 1662-1675)
- Cache update logic (lines 1803-1814)
- **ZERO test coverage** for this critical path

## Proposed Refactoring Strategy

### Phase 1: Extract View Presentation Logic

**Create**: `moneyflow/view_presenter.py`

**Responsibility**: Transform data into UI-ready format

```python
class ViewPresenter:
    """Handles presentation logic for different views."""

    @staticmethod
    def prepare_aggregation_view(
        df: pl.DataFrame,
        group_by_field: str,  # 'merchant', 'category', 'group', 'account'
        sort_by: SortMode,
        sort_direction: SortDirection
    ) -> dict:
        """
        Prepare aggregated data for display.

        Returns:
            {
                'columns': [('Name', 40), ('Count', 10), ('Total', 15)],
                'rows': [('Amazon', '50', '$1,234.56'), ...],
                'headers': {'count': 'Count ↓', 'total': 'Total'}
            }
        """

    @staticmethod
    def prepare_transaction_view(
        df: pl.DataFrame,
        sort_by: SortMode,
        sort_direction: SortDirection,
        pending_edits: set,
        selected_ids: set
    ) -> dict:
        """Prepare transaction list for display with flags."""

    @staticmethod
    def compute_transaction_flags(
        txn_id: str,
        is_selected: bool,
        is_hidden: bool,
        has_pending_edit: bool
    ) -> str:
        """Compute display flags: ✓ H *"""
```

**Benefits**:
- Testable presentation logic
- Eliminates 190+ lines of duplication
- UI layer becomes thin rendering wrapper

### Phase 2: Extract Time Navigation Logic

**Create**: `moneyflow/time_navigator.py`

**Responsibility**: Date calculations and period navigation

```python
class TimeNavigator:
    """Handles time period calculations."""

    @staticmethod
    def select_month(year: int, month: int) -> tuple[date, date]:
        """Get first and last day of month."""

    @staticmethod
    def previous_period(
        start_date: date,
        end_date: date
    ) -> tuple[date, date, str]:
        """
        Navigate to previous period.

        Returns: (new_start, new_end, description)
        Example: (date(2024, 11, 1), date(2024, 11, 30), "November 2024")
        """

    @staticmethod
    def next_period(
        start_date: date,
        end_date: date
    ) -> tuple[date, date, str]:
        """Navigate to next period."""

    @staticmethod
    def is_full_year(start_date: date, end_date: date) -> bool:
        """Check if date range is a full year."""
```

**Benefits**:
- All date math in one place
- Easy to test edge cases
- Clear separation of concerns

### Phase 3: Extract Edit Workflow Controller

**Create**: `moneyflow/edit_controller.py`

**Responsibility**: Edit operation orchestration

```python
class EditController:
    """Orchestrates edit operations."""

    def __init__(self, data_manager: DataManager, state: AppState):
        self.data_manager = data_manager
        self.state = state

    def prepare_merchant_edit(
        self,
        current_data: pl.DataFrame,
        cursor_row: int,
        all_merchants: list[str]
    ) -> dict:
        """
        Prepare merchant edit context.

        Returns:
            {
                'mode': 'single' | 'bulk' | 'aggregate',
                'merchant': str,
                'count': int,
                'transactions': pl.DataFrame,
                'suggestions': list[str],
                'summary': dict  # for bulk edits
            }
        """

    def queue_merchant_edits(
        self,
        transactions: pl.DataFrame,
        old_merchant: str,
        new_merchant: str
    ) -> int:
        """Queue merchant edits and return count."""

    def prepare_recategorize(
        self,
        current_data: pl.DataFrame,
        cursor_row: int
    ) -> dict:
        """Prepare recategorize context."""

    def queue_category_edits(
        self,
        transaction_ids: list[str],
        new_category_id: str
    ) -> int:
        """Queue category edits and return count."""
```

**Benefits**:
- Business rules separate from UI
- Testable edit workflows
- Reusable across different UIs

### Phase 4: Extract Commit Orchestrator

**Create**: `moneyflow/commit_orchestrator.py`

**Responsibility**: Commit workflow with retry and DataFrame updates

```python
class CommitOrchestrator:
    """Handles commit workflow with retries and local updates."""

    def __init__(
        self,
        data_manager: DataManager,
        state: AppState,
        cache_manager: Optional[CacheManager] = None
    ):
        self.data_manager = data_manager
        self.state = state
        self.cache_manager = cache_manager

    async def commit_with_retry(
        self,
        edits: list[TransactionEdit],
        credential_refresher: Optional[callable] = None
    ) -> tuple[int, int]:
        """
        Commit edits with automatic retry on session expiration.

        Args:
            edits: List of edits to commit
            credential_refresher: Optional callback to refresh credentials

        Returns:
            (success_count, failure_count)
        """

    def apply_edits_to_dataframe(
        self,
        df: pl.DataFrame,
        edits: list[TransactionEdit],
        categories: dict
    ) -> pl.DataFrame:
        """
        Apply edits to DataFrame for instant UI update.

        Pure function - no side effects.
        """

    async def update_cache(
        self,
        year_filter: Optional[int],
        since_filter: Optional[str]
    ) -> bool:
        """Update cache with committed changes."""
```

**Benefits**:
- Critical commit logic becomes testable
- Retry strategy is reusable
- DataFrame updates are pure functions
- Clear error handling

## Code Duplication Analysis

### Pattern 1: Aggregation Views (4x duplication)

**Current**: 192 lines across 4 methods
**After refactoring**: ~50 lines total

**Savings**: 140 lines (73% reduction)

### Pattern 2: Sort Header Generation (4x duplication)

```python
# Repeated 4 times:
arrow = "↓" if self.state.sort_direction == SortDirection.DESC else "↑"
count_header = "Count " + arrow if self.state.sort_by == SortMode.COUNT else "Count"
amount_header = "Total " + arrow if self.state.sort_by == SortMode.AMOUNT else "Total"
```

**Solution**: Extract to `ViewPresenter.get_column_headers()`

### Pattern 3: Sort Direction Inversion (5x duplication)

```python
# Amount sorting: invert direction so largest expenses come first
descending = (
    self.state.sort_direction == SortDirection.ASC
    if sort_col == "total"
    else self.state.sort_direction == SortDirection.DESC
)
```

**Solution**: Extract to `ViewPresenter.get_sort_descending()`

### Pattern 4: Edit Context Building (3x duplication)

Similar patterns in:
- `_bulk_edit_merchant_from_aggregate()`
- `_edit_merchant_detail()`
- `_recategorize()`

**Solution**: Extract to `EditController.prepare_*()` methods

## Test Coverage Gaps

Current test coverage analysis shows:

### Untested UI Logic (0% coverage):
1. Aggregation view rendering (192 lines)
2. Transaction view rendering (82 lines)
3. Time navigation actions (154 lines)
4. Edit workflows (384 lines)
5. Commit with DataFrame updates (150 lines)

### After Refactoring (Target: 90%+ coverage):
1. ViewPresenter: 100% testable
2. TimeNavigator: 100% testable
3. EditController: 100% testable
4. CommitOrchestrator: 100% testable

**Total new test-covered code**: ~800 lines moved from 0% to 90%+

## Implementation Plan

### Step 1: Extract ViewPresenter (Low Risk)
- Create view_presenter.py
- Add comprehensive tests
- Update app.py show_* methods to use presenter
- Run full test suite

### Step 2: Extract TimeNavigator (Low Risk)
- Create time_navigator.py
- Add tests for edge cases
- Update action_* methods
- Run full test suite

### Step 3: Extract EditController (Medium Risk)
- Create edit_controller.py
- Add workflow tests
- Update edit action methods incrementally
- Run tests after each change

### Step 4: Extract CommitOrchestrator (High Risk)
- Create commit_orchestrator.py
- Add extensive tests for DataFrame updates
- Add retry tests
- Update commit workflow
- **Extensive manual QA required**

### Step 5: Delete Duplicate Code
- Remove duplicated logic from app.py
- Final test pass
- Manual QA pass

## Success Metrics

1. **Code Reduction**: app.py from 2000 lines to ~1200 lines
2. **Test Coverage**: Business logic from 0% to 90%+
3. **Duplication**: Eliminate 250+ lines of duplicate code
4. **Testability**: 4 new pure-logic modules, fully tested
5. **Maintainability**: Clear separation of concerns

## Risk Mitigation

1. **No UI tests**: Manual QA required after each refactoring phase
2. **DataFrame operations**: Add explicit tests for each edit type
3. **Async operations**: Test retry logic with mocks
4. **State management**: Ensure no unintended state mutations

## Timeline Estimate

- **Phase 1** (ViewPresenter): 2-3 hours
- **Phase 2** (TimeNavigator): 1-2 hours
- **Phase 3** (EditController): 3-4 hours
- **Phase 4** (CommitOrchestrator): 4-5 hours
- **Phase 5** (Cleanup): 1 hour
- **Manual QA**: 2 hours

**Total**: 13-17 hours of focused work

## Next Steps

1. Get approval for refactoring approach
2. Start with Phase 1 (ViewPresenter) - lowest risk
3. Write tests first for each extracted component
4. Refactor incrementally with test runs between changes
5. Manual QA at end of each phase

---

**Note**: This is a comprehensive refactoring. We can proceed incrementally, validating each phase before moving to the next.
