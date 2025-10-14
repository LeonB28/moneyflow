# Controller Facade Refactoring Plan

## Problem

MoneyflowTUI currently juggles three objects with overlapping responsibilities:
- `self.state` - 50+ direct accesses
- `self.data_manager` - 26+ direct accesses
- `self.controller` - Used for some operations

This creates:
- **Leaky abstraction**: UI knows too much about internal state structure
- **Tight coupling**: Can't change state/data_manager without touching UI
- **Hard to test**: UI layer mixed with business logic decisions
- **Inconsistent**: Some operations use controller, others access state/data_manager directly

## Goal

**Single point of contact**: MoneyflowTUI should only interact with `self.controller`

```python
# Before (scattered):
self.state.view_mode = ViewMode.MERCHANT
self.state.selected_merchant = None
filtered_df = self.state.get_filtered_df()
merchants = self.data_manager.df["merchant"].unique().to_list()
self.controller.queue_merchant_edits(...)

# After (facade):
self.controller.switch_to_merchant_view()
merchants = self.controller.get_merchant_suggestions()
self.controller.queue_merchant_edits(...)
```

## Architecture Change

### Current (Fragmented)
```
MoneyflowTUI
  ├─→ state (AppState) - view state, filtering
  ├─→ data_manager (DataManager) - data, categories
  └─→ controller (AppController) - some business logic

Problems:
- MoneyflowTUI knows about state internals (view_mode, selected_*, sort_by)
- MoneyflowTUI accesses data_manager for categories, df
- Responsibilities unclear
```

### Proposed (Facade)
```
MoneyflowTUI
  └─→ controller (AppController) - single facade
        ├─ state (private) - encapsulated
        ├─ data_manager (private) - encapsulated
        └─ public methods - clean interface

Benefits:
- MoneyflowTUI is thin UI orchestration
- Controller owns all business logic
- State/DataManager are implementation details
- Easy to mock controller for UI tests
```

## Refactoring Phases

### Phase 1: Move Ownership into Controller ✅

**Change**: `state` and `data_manager` become private `_state` and `_data_manager`

```python
class AppController:
    def __init__(self, view, state, data_manager, cache_manager):
        self.view = view
        self._state = state  # Private - don't expose
        self._data_manager = data_manager  # Private
        self.cache_manager = cache_manager
```

**Impact**: Tests continue to work (they already pass state/data_manager to controller)

---

### Phase 2: Add Facade Methods to Controller

Group by functionality:

#### **View Mode Operations**
```python
def switch_to_merchant_view(self):
    """Switch to merchant aggregation view."""
    self._state.view_mode = ViewMode.MERCHANT
    self._state.selected_merchant = None
    self._state.selected_category = None
    self._state.selected_group = None
    self._state.selected_account = None
    if self._state.sort_by not in [SortMode.COUNT, SortMode.AMOUNT]:
        self._state.sort_by = SortMode.AMOUNT
    self.refresh_view()

def switch_to_detail_view(self, default_sort=True):
    """Switch to transaction detail view."""
    self._state.view_mode = ViewMode.DETAIL
    self._state.selected_merchant = None
    self._state.selected_category = None
    self._state.selected_group = None
    self._state.selected_account = None
    if default_sort:
        self._state.sort_by = SortMode.DATE
        self._state.sort_direction = SortDirection.DESC
    self.refresh_view()

def cycle_grouping(self) -> Optional[str]:
    """Cycle through aggregate views. Returns view name or None."""
    view_name = self._state.cycle_grouping()
    if view_name:
        self.refresh_view()
    return view_name

def drill_down(self, item_name: str, cursor_position: int):
    """Drill down into an item (merchant/category/etc)."""
    self._state.drill_down(item_name, cursor_position)
    self.refresh_view()

def go_back(self) -> tuple[bool, int]:
    """Go back to previous view. Returns (success, cursor_position)."""
    success, cursor_position = self._state.go_back()
    if success:
        self.refresh_view()
    return (success, cursor_position)
```

#### **Sorting Operations**
```python
def toggle_sort_field(self) -> str:
    """Toggle sort field. Returns display name."""
    new_sort, display = self.get_next_sort_field(self._state.view_mode, self._state.sort_by)
    self._state.sort_by = new_sort
    self.refresh_view()
    return display

def reverse_sort(self) -> str:
    """Reverse sort direction. Returns direction name."""
    self._state.reverse_sort()
    self.refresh_view()
    direction = "Descending" if self._state.sort_direction == SortDirection.DESC else "Ascending"
    return direction
```

#### **Time Navigation**
```python
def set_timeframe_this_year(self):
    """Set view to current year."""
    self._state.set_timeframe(TimeFrame.THIS_YEAR)
    self.refresh_view()

def set_timeframe_all_time(self):
    """Set view to all time."""
    self._state.set_timeframe(TimeFrame.ALL_TIME)
    self.refresh_view()

def set_timeframe_this_month(self):
    """Set view to current month."""
    self._state.set_timeframe(TimeFrame.THIS_MONTH)
    self.refresh_view()

def navigate_prev_period(self) -> tuple[bool, Optional[str]]:
    """Navigate to previous period. Returns (should_fallback_to_year, description)."""
    if self._state.start_date is None:
        return (True, None)  # Signal: fallback to this year

    date_range = TimeNavigator.previous_period(self._state.start_date, self._state.end_date)
    self._state.set_timeframe(
        TimeFrame.CUSTOM,
        start_date=date_range.start_date,
        end_date=date_range.end_date
    )
    self.refresh_view()
    return (False, date_range.description)

def navigate_next_period(self) -> tuple[bool, Optional[str]]:
    """Navigate to next period. Returns (should_fallback_to_year, description)."""
    # Same pattern as prev
```

#### **Search & Filtering**
```python
def apply_search(self, query: str) -> int:
    """Apply search query. Returns result count."""
    self._state.search_query = query
    self.refresh_view()
    filtered = self._state.get_filtered_df()
    return len(filtered) if filtered is not None else 0

def apply_filters(self, show_transfers: bool, show_hidden: bool):
    """Apply visibility filters."""
    self._state.show_transfers = show_transfers
    self._state.show_hidden = show_hidden
    self.refresh_view()

def toggle_selection(self, txn_id: str) -> int:
    """Toggle transaction selection. Returns total selected count."""
    self._state.toggle_selection(txn_id)
    self.refresh_view()
    return len(self._state.selected_ids)

def clear_selection(self):
    """Clear all selections."""
    self._state.clear_selection()
```

#### **Data Access (Read-only)**
```python
def get_filtered_df(self):
    """Get filtered DataFrame for current view."""
    return self._state.get_filtered_df()

def get_current_data(self):
    """Get current view data (aggregated or detail)."""
    return self._state.current_data

def get_merchant_suggestions(self) -> list[str]:
    """Get list of all merchants for autocomplete."""
    if self._data_manager.df is None:
        return []
    return self._data_manager.df["merchant"].unique().to_list()

def get_categories(self) -> dict:
    """Get category map."""
    return self._data_manager.categories

def get_pending_changes_count(self) -> int:
    """Get count of pending edits."""
    return self._data_manager.get_stats()["pending_changes"]

def get_pending_edits(self):
    """Get pending edits for review."""
    return self._data_manager.pending_edits

def has_unsaved_changes(self) -> bool:
    """Check if there are unsaved changes."""
    return self.get_pending_changes_count() > 0
```

#### **View State Queries**
```python
def get_view_mode(self) -> ViewMode:
    """Get current view mode."""
    return self._state.view_mode

def get_selected_ids(self) -> set:
    """Get currently selected transaction IDs."""
    return self._state.selected_ids

def get_selected_count(self) -> int:
    """Get count of selected transactions."""
    return len(self._state.selected_ids)
```

---

### Phase 3: Update MoneyflowTUI

**Remove direct access**:
```python
# Remove these from MoneyflowTUI:
self.state = None  # Delete
self.data_manager = None  # Delete

# Keep only:
self.controller = None
```

**Update all action methods**:
```python
# Before:
def action_view_merchants(self):
    self.state.view_mode = ViewMode.MERCHANT
    self.state.selected_merchant = None
    ...
    self.refresh_view()

# After:
def action_view_merchants(self):
    self.controller.switch_to_merchant_view()
```

---

### Phase 4: Benefits

✅ **Clean interface**: MoneyflowTUI talks to one object
✅ **Testable**: Mock controller.switch_to_merchant_view() in UI tests
✅ **Encapsulation**: State/DataManager are private implementation details
✅ **Consistent**: All operations go through controller
✅ **Maintainable**: Changes to state structure don't ripple to UI

---

## Implementation Strategy

### Order of Operations:

1. **Add facade methods to AppController** (non-breaking)
2. **Update app.py methods one by one** to use facade
3. **Run tests after each method** to ensure no regressions
4. **Once all migrated**, make state/data_manager private in controller
5. **Update tests** to not access private members directly

### Estimated Scope:

- **~50 state accesses** → ~15 facade methods
- **~26 data_manager accesses** → ~5 facade methods
- **Total**: ~20 new controller methods
- **Migrations**: ~40 app.py methods to update

### Risk Mitigation:

- Do incrementally (one action method at a time)
- Run full test suite after each change
- Keep git commits granular for easy rollback
- Don't change behavior, just refactor structure

---

## Next Steps

1. Start with **view mode switching** (highest impact, easiest)
2. Then **sorting operations** (already started)
3. Then **time navigation** (moderate complexity)
4. Then **data access methods** (simple getters)
5. Finally **cleanup**: Make state/data_manager private

Want me to start implementing this?
