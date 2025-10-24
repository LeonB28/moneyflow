# moneyflow Architecture Refactoring Plan

**Goal:** Extract business logic from `app.py` into controller/model layers to enable:
1. Alternative UI implementations (web UI, CLI, API)
2. Comprehensive unit testing of business logic
3. Better separation of concerns
4. Easier maintenance and feature development

**Current State Analysis**

- `app.py`: 2,481 lines, 58 methods
- `app_controller.py`: 934 lines, 42 methods
- `state.py`: Mostly pure state management
- `data_manager.py`: Data operations and API integration

---

## Current Architecture Assessment

### ✅ Already Well-Separated

**app_controller.py (Good separation):**
- View refresh logic (`refresh_view()`, `_prepare_aggregate_view()`)
- View mode switching (`switch_to_*_view()`)
- Time navigation (`set_timeframe_*()`, `navigate_*_period()`)
- Sort operations (`toggle_sort_field()`, `reverse_sort()`)
- Edit queueing (`queue_category_edits()`, `queue_merchant_edits()`, `queue_hide_toggle_edits()`)
- Multi-select helpers (`get_transactions_from_selected_groups()`)
- Search operations (`apply_search()`, `clear_search()`)
- Commit result handling (`handle_commit_result()`)

**state.py (Good separation):**
- Navigation state management
- Drill-down logic
- Time frame management
- Filter state
- Undo/redo stacks (partially used)

**data_manager.py (Good separation):**
- Data fetching with pagination
- DataFrame transformations
- Aggregation operations
- Filtering operations
- API integration

### ❌ Business Logic Still in app.py (Needs Extraction)

#### 1. **Edit Orchestration Logic** (HIGH PRIORITY)

**Current location:** app.py
- `action_edit_merchant()` - 200+ lines
- `action_edit_category()` - 180+ lines
- `_bulk_edit_merchant_from_aggregate()`
- `_bulk_edit_merchant_from_selected_groups()`
- `_bulk_edit_category_from_aggregate()`
- `_bulk_edit_category_from_selected_groups()`
- `_edit_merchant_detail()`
- `_edit_category()`

**Business Logic Embedded:**
- Determining edit context (aggregate vs detail vs multi-select)
- Getting transactions to edit based on view state
- Showing modals and processing results
- Queueing edits with proper old/new values
- Validation (empty strings, whitespace, etc.)

**Why this is problematic:**
- Cannot test edit workflows without TUI
- Logic duplicated across merchant/category edit methods
- Hard to understand the complete edit flow
- Cannot reuse in other UIs

**Extraction Target:** `EditOrchestrator` class or methods in `app_controller.py`

**What should be extracted:**
```python
# Controller layer (testable)
controller.edit_merchant_current_selection(new_merchant: str) -> int
controller.edit_category_current_selection(new_category_id: str) -> int
controller.determine_edit_context() -> EditContext  # aggregate/detail/multi-select
controller.get_transactions_to_edit() -> pl.DataFrame
controller.validate_merchant_name(name: str) -> bool

# UI layer (stays in app.py)
action_edit_merchant()  # Shows modal, calls controller methods
_show_merchant_modal()  # Pure UI
```

**Testing benefit:**
```python
def test_bulk_merchant_edit_from_aggregate_view():
    # Set up state
    controller.state.view_mode = ViewMode.MERCHANT
    controller.state.current_data = merchant_agg_df

    # Execute business logic
    count = controller.edit_merchant_current_selection("Amazon")

    # Verify
    assert count == 50  # All Amazon transactions edited
    assert len(controller.data_manager.pending_edits) == 50
```

---

#### 2. **Hide/Unhide Orchestration** (HIGH PRIORITY)

**Current location:** app.py `action_toggle_hide_from_reports()` - 160 lines

**Business Logic Embedded:**
- Determining if aggregate vs detail vs sub-grouped view
- Getting transactions based on view type
- Detecting if multi-select is active
- Checking for existing pending hide toggle (undo logic)
- Queueing hide toggle edits

**Why this is problematic:**
- Complex conditional logic based on view state
- Cannot test hide/unhide workflows without TUI
- Duplicates pattern from edit methods
- 160 lines in single method!

**Extraction Target:** `controller.toggle_hide_current_selection() -> int`

---

#### 3. **Delete Transaction Logic** (MEDIUM PRIORITY)

**Current location:** app.py
- `action_delete_transaction()`
- `_delete_transaction()` - 70 lines
- `_delete_with_retry()` - session renewal logic

**Business Logic Embedded:**
- Determining single vs multi-select delete
- Deleting via API with session renewal
- Updating local DataFrame to remove deleted transactions
- Error handling with partial failure support

**Why this is problematic:**
- DataFrame mutation logic embedded in UI
- Cannot test delete workflows
- Session renewal should be generalized (not delete-specific)

**Extraction Target:**
```python
controller.delete_current_selection() -> tuple[int, int]  # success_count, failure_count
controller.delete_transactions(transaction_ids: list[str]) -> tuple[int, int]
# Session renewal should be in a shared retry/auth helper
```

---

#### 4. **Multi-Select Logic** (MEDIUM PRIORITY)

**Current location:** app.py
- `action_toggle_select()` - 90 lines
- `action_select_all()` - 80 lines

**Business Logic Embedded:**
- Determining if aggregate vs detail vs sub-grouped view
- Group selection vs transaction selection
- Select all logic with view-specific handling
- Cursor position management

**Why this is problematic:**
- Selection logic mixed with cursor management
- Cannot test multi-select patterns
- View-specific branching should be controller's responsibility

**Extraction Target:**
```python
controller.toggle_selection_current_row() -> tuple[bool, int]  # is_selected, count
controller.select_all_visible() -> int
controller.clear_selection()  # Already exists, but could be enhanced
```

---

#### 5. **Undo/Redo Logic** (MEDIUM PRIORITY)

**Current location:** app.py `action_undo_pending_edits()` - 50 lines

**Business Logic Embedded:**
- Bulk edit detection by timestamp
- Removing edits from pending queue
- Counting undone edits
- Determining notification message

**Why this is problematic:**
- Undo/redo is business logic, not UI logic
- state.py has undo_stack/redo_stack but they're not used
- Cannot test undo behavior without TUI

**Extraction Target:**
```python
controller.undo_recent_edits() -> tuple[int, str]  # count_undone, field_name
# Or better: Use state.undo_last_edit() from state.py (currently unused!)
```

**Note:** state.py already has `undo_stack` and `undo_last_edit()` but they're not connected to the UI. This should be integrated.

---

#### 6. **Session Management & Authentication** (LOW PRIORITY - Complex)

**Current location:** app.py
- `_do_fresh_login()` - 25 lines
- `_refresh_session()` - 30 lines
- `_login_with_retry()` - 80 lines
- `_commit_with_retry()` - 100 lines
- `_delete_with_retry()` - 30 lines

**Business Logic Embedded:**
- Session expiration detection (401/unauthorized/token errors)
- Credential loading and refresh
- Retry logic with exponential backoff
- Error message parsing

**Why this is problematic:**
- Session renewal scattered across delete/commit/fetch
- Retry logic duplicated
- Cannot test authentication flows

**Extraction Target:**
- `SessionManager` class to centralize session renewal
- Decorator or wrapper for API calls that auto-renews on 401
- Separate `RetryPolicy` for backoff logic

**Example:**
```python
@auto_renew_session
async def commit_edits(edits):
    return await backend.commit(edits)

# SessionManager handles 401s automatically
```

---

#### 7. **Data Initialization & Loading** (LOW PRIORITY)

**Current location:** app.py
- `initialize_data()` - 120 lines
- `_handle_credentials()` - 60 lines
- `_check_and_load_cache()` - 50 lines
- `_fetch_data_with_retry()` - 80 lines

**Business Logic Embedded:**
- Credential flow (unlock, backend selection, setup)
- Cache validation and loading
- Data fetching with progress callbacks
- Error handling and recovery

**Why this is problematic:**
- Initialization is tightly coupled to Textual lifecycle
- Cannot test loading flows
- Progress callbacks are UI-specific

**Extraction Target:**
- `DataLoader` class to handle fetch/cache/credentials flow
- Return structured results, let UI handle display
- Separate progress reporting from business logic

---

#### 8. **Duplicate Detection UI Logic** (LOW PRIORITY)

**Current location:** app.py `action_find_duplicates()` - 20 lines

**Status:** Mostly good - calls `DuplicateDetector.find_duplicates()`

**Remaining UI coupling:** Showing duplicates screen

This is already well-separated. ✅

---

## Refactoring Priorities

### **Phase 1: Edit Orchestration (Highest Impact)**

**Complexity:** Medium
**Benefit:** High - most complex business logic, enables testing of primary use case
**Effort:** 2-3 days

**Goals:**
1. Extract edit context determination to controller
2. Unify merchant/category edit logic (reduce duplication)
3. Create `controller.edit_current_selection()` method
4. Make edit logic testable without UI

**Deliverables:**
- `EditContext` dataclass (aggregate/detail/multi-select + metadata)
- `controller.determine_edit_context() -> EditContext`
- `controller.edit_merchant_current_selection(new_merchant: str) -> int`
- `controller.edit_category_current_selection(new_category_id: str) -> int`
- Comprehensive unit tests for all edit scenarios

**Success Metrics:**
- app.py edit methods reduced by 60%
- 20+ new unit tests for edit workflows
- Edit logic fully testable without TUI

---

### **Phase 2: Hide/Unhide & Multi-Select (Medium Impact)**

**Complexity:** Medium
**Benefit:** Medium - reduces app.py size, enables testing
**Effort:** 1-2 days

**Goals:**
1. Extract hide/unhide orchestration
2. Extract multi-select logic
3. Standardize selection handling

**Deliverables:**
- `controller.toggle_hide_current_selection() -> int`
- `controller.toggle_selection_current_row() -> tuple[bool, int]`
- `controller.select_all_visible() -> int`
- Unit tests for all selection patterns

---

### **Phase 3: Undo/Redo Integration (Low Complexity, High Value)**

**Complexity:** Low
**Benefit:** High - connects existing unused infrastructure
**Effort:** 1 day

**Goals:**
1. Connect UI undo to state.undo_last_edit()
2. Use state.undo_stack properly
3. Add redo support (state.redo_stack exists but unused)
4. Generalize bulk undo

**Deliverables:**
- Integrate with existing state.py undo infrastructure
- Add redo keybinding (Ctrl+Y or similar)
- Tests for undo/redo workflows

---

### **Phase 4: Delete Orchestration (Medium Priority)**

**Complexity:** Medium (session renewal complexity)
**Benefit:** Medium
**Effort:** 1-2 days

**Goals:**
1. Extract delete logic to controller
2. Generalize session renewal (apply to all API calls)
3. Standardize DataFrame mutation

**Deliverables:**
- `controller.delete_current_selection() -> tuple[int, int]`
- Generalized `@with_session_renewal` decorator
- Tests for delete workflows

---

### **Phase 5: Session Management (Optional - Complex)**

**Complexity:** High
**Benefit:** Low (current approach works)
**Effort:** 3-4 days

**Note:** This is architectural cleanup, not critical for functionality.

Only pursue if:
- Planning to add multiple backends with different auth patterns
- Need to support long-running background operations
- Want to eliminate all retry logic duplication

---

## Detailed Refactoring Guide: Phase 1 (Edit Orchestration)

### Step 1: Define EditContext

```python
# In app_controller.py or new edit_orchestrator.py

@dataclass
class EditContext:
    """Context for determining how to handle an edit operation."""

    mode: EditMode  # AGGREGATE_SINGLE, AGGREGATE_MULTI, DETAIL_SINGLE, DETAIL_MULTI, SUBGROUP_SINGLE, SUBGROUP_MULTI
    view_mode: ViewMode
    transactions: pl.DataFrame  # Transactions to edit
    current_value: str | None  # Current merchant/category value
    is_multi_select: bool
    group_field: str | None  # For aggregate edits

class EditMode(Enum):
    AGGREGATE_SINGLE = "aggregate_single"  # Press m on one merchant in aggregate view
    AGGREGATE_MULTI = "aggregate_multi"    # Multi-select merchants, press m
    DETAIL_SINGLE = "detail_single"        # Press m on one transaction in detail
    DETAIL_MULTI = "detail_multi"          # Multi-select transactions, press m
    SUBGROUP_SINGLE = "subgroup_single"    # Press m in sub-grouped view
    SUBGROUP_MULTI = "subgroup_multi"      # Multi-select in sub-grouped view
```

### Step 2: Extract Context Determination

```python
# In app_controller.py

def determine_edit_context(self, field_type: str) -> EditContext:
    """
    Determine edit context based on current view and selection state.

    Args:
        field_type: "merchant" or "category"

    Returns:
        EditContext with mode, transactions, current value, etc.
    """
    # Current view state
    view_mode = self.state.view_mode
    is_detail = view_mode == ViewMode.DETAIL
    is_aggregate = view_mode in [ViewMode.MERCHANT, ViewMode.CATEGORY, ViewMode.GROUP, ViewMode.ACCOUNT]
    is_subgrouped = self.state.is_drilled_down() and self.state.sub_grouping_mode

    # Selection state
    has_selected_ids = len(self.state.selected_ids) > 0
    has_selected_groups = len(self.state.selected_group_keys) > 0

    # Determine mode and get transactions
    if is_aggregate or is_subgrouped:
        # ... logic to determine AGGREGATE_SINGLE vs AGGREGATE_MULTI
        # ... get transactions for current group or selected groups
        pass
    elif is_detail:
        # ... logic to determine DETAIL_SINGLE vs DETAIL_MULTI
        # ... get current transaction or selected transactions
        pass

    return EditContext(...)
```

### Step 3: Extract Edit Execution

```python
# In app_controller.py

def edit_merchant_current_selection(self, new_merchant: str) -> int:
    """
    Edit merchant for current selection (context-aware).

    Handles all edit modes: aggregate single/multi, detail single/multi, subgroup.

    Returns:
        Number of edits queued
    """
    context = self.determine_edit_context("merchant")

    if not context.transactions or context.transactions.is_empty():
        return 0

    # Validate
    if not new_merchant or not new_merchant.strip():
        return 0

    # Queue edits using existing helper
    return self.queue_merchant_edits(
        context.transactions,
        context.current_value or "",
        new_merchant
    )
```

### Step 4: Simplify UI Layer

```python
# In app.py (much simpler now)

def action_edit_merchant(self) -> None:
    """Edit merchant for current selection."""
    if self.data_manager is None:
        return

    # Get edit context (knows what to edit)
    context = self.controller.determine_edit_context("merchant")
    if context.transactions.is_empty():
        self.notify("No transactions to edit", timeout=2)
        return

    # Show modal (UI concern)
    self.run_worker(self._show_merchant_modal(context), exclusive=False)

async def _show_merchant_modal(self, context: EditContext) -> None:
    """Show merchant edit modal and process result."""
    # Get merchant suggestions
    all_merchants = self.controller.get_merchant_suggestions()

    # Show modal
    new_merchant = await self.push_screen(
        EditMerchantScreen(
            current_merchant=context.current_value or "",
            transaction_count=len(context.transactions),
            all_merchants=all_merchants,
            transaction_details=context.get_display_details()
        ),
        wait_for_dismiss=True
    )

    if new_merchant:
        # Execute edit (business logic in controller)
        count = self.controller.edit_merchant_current_selection(new_merchant)

        # Show result (UI concern)
        self._notify(NotificationHelper.edit_queued(count))
        self.refresh_view()
```

**Before:** 200+ lines in app.py with complex branching
**After:** 30 lines in app.py + testable logic in controller

---

### Step 5: Unit Tests

```python
# tests/test_edit_orchestrator.py (new file)

class TestEditContextDetermination:
    """Test edit context is correctly determined for all view states."""

    async def test_aggregate_view_single_merchant(self, controller):
        """Merchant view, press m on one merchant."""
        controller.state.view_mode = ViewMode.MERCHANT
        controller.state.current_data = create_merchant_aggregation()

        context = controller.determine_edit_context("merchant")

        assert context.mode == EditMode.AGGREGATE_SINGLE
        assert len(context.transactions) > 0
        assert context.current_value == "Amazon"  # Current row

    async def test_aggregate_view_multi_select(self, controller):
        """Merchant view, multi-select 3 merchants, press m."""
        controller.state.view_mode = ViewMode.MERCHANT
        controller.state.selected_group_keys = {"Amazon", "Walmart", "Target"}

        context = controller.determine_edit_context("merchant")

        assert context.mode == EditMode.AGGREGATE_MULTI
        assert context.is_multi_select is True
        # Transactions from all 3 merchants

    async def test_detail_view_single_transaction(self, controller):
        """Detail view, press m on one transaction."""
        controller.state.view_mode = ViewMode.DETAIL

        context = controller.determine_edit_context("merchant")

        assert context.mode == EditMode.DETAIL_SINGLE
        assert len(context.transactions) == 1

    async def test_detail_view_multi_select(self, controller):
        """Detail view, multi-select 5 transactions, press m."""
        controller.state.view_mode = ViewMode.DETAIL
        controller.state.selected_ids = {f"txn_{i}" for i in range(5)}

        context = controller.determine_edit_context("merchant")

        assert context.mode == EditMode.DETAIL_MULTI
        assert len(context.transactions) == 5

    async def test_subgrouped_view(self, controller):
        """Drilled into merchant, sub-grouped by category, press m."""
        controller.state.view_mode = ViewMode.DETAIL
        controller.state.selected_merchant = "Amazon"
        controller.state.sub_grouping_mode = ViewMode.CATEGORY

        context = controller.determine_edit_context("merchant")

        assert context.mode == EditMode.SUBGROUP_SINGLE
        # Should get transactions for current sub-group row


class TestEditExecution:
    """Test edit execution logic."""

    async def test_edit_merchant_bulk_from_aggregate(self, controller):
        """Test bulk merchant edit from aggregate view."""
        # Setup: Merchant view with Amazon selected
        controller.state.view_mode = ViewMode.MERCHANT
        # ... setup current_data with Amazon row

        count = controller.edit_merchant_current_selection("Amazon.com")

        assert count == 50  # All Amazon transactions
        assert len(controller.data_manager.pending_edits) == 50
        assert all(e.field == "merchant" for e in controller.data_manager.pending_edits)
        assert all(e.new_value == "Amazon.com" for e in controller.data_manager.pending_edits)
```

---

## Architectural Principles

### Separation of Concerns

**UI Layer (app.py):**
- Handle Textual events (key presses, widget events)
- Show modals and screens
- Display notifications
- Manage cursor and scroll position
- Call controller methods with user input
- Format and display results

**Controller Layer (app_controller.py):**
- Determine what to do based on state
- Get correct data for operations
- Execute business operations
- Return results (counts, success/failure)
- NO UI dependencies (no modals, no notify, no widgets)

**Model Layer (state.py, data_manager.py):**
- Pure state management
- Data transformations
- API integration
- NO UI dependencies
- NO controller dependencies

### Testing Strategy

**Current Coverage:**
- state.py: 89% (good)
- data_manager.py: 98% (excellent)
- app_controller.py: 84% (good, can improve)
- app.py: 0% (expected - Textual integration tests are hard)

**After Refactoring:**
- app_controller.py: 95%+ (comprehensive business logic tests)
- New edit_orchestrator.py: 95%+ (all edit workflows tested)
- app.py: Still ~0% (but much simpler, less logic to test)

### Benefits of This Refactoring

**1. Alternative UIs Become Possible:**
```python
# Web UI example
@app.post("/api/edit_merchant")
async def api_edit_merchant(merchant_id: str, new_name: str):
    # Reuse same controller logic
    controller = get_controller()
    controller.state.view_mode = ViewMode.MERCHANT
    controller.state.current_data = get_merchant_by_id(merchant_id)

    count = controller.edit_merchant_current_selection(new_name)
    return {"edits_queued": count}
```

**2. CLI Batch Operations:**
```python
# Command-line bulk edit
moneyflow edit-merchant --from="AMZN*" --to="Amazon" --dry-run

# Uses same controller logic
controller.state.view_mode = ViewMode.MERCHANT
controller.filter_by_merchant("AMZN*")
count = controller.edit_merchant_current_selection("Amazon")
```

**3. Comprehensive Testing:**
- Test all edit modes (6 modes) × (merchant/category/hide) = 18 test cases
- Test multi-level drill-down with edits
- Test error cases (empty input, validation)
- Test undo/redo workflows
- All testable without spinning up TUI

**4. Easier Maintenance:**
- Edit logic in one place (controller)
- UI code much simpler (show modal, call controller, display result)
- Bugs easier to fix (business logic is isolated)
- Features easier to add (implement in controller, wire up UI)

---

## Implementation Approach

### Incremental Refactoring

**Don't rewrite everything at once!** Refactor incrementally:

1. **Extract one method** (e.g., `determine_edit_context()`)
2. **Write tests** for that method
3. **Use it in app.py** alongside old code
4. **Verify no regressions**
5. **Remove old code** once new code is proven
6. **Repeat** for next method

### Backward Compatibility

Maintain current functionality while refactoring:
- Don't change user-facing behavior
- Keep all existing tests passing
- New controller methods should complement existing ones
- Only remove app.py code once controller is proven

---

## Open Questions / Decisions Needed

### 1. EditOrchestrator vs Controller Methods?

**Option A:** Add methods to existing `AppController`
- Pro: Simpler, fewer files
- Con: AppController gets large (already 934 lines)

**Option B:** Create separate `EditOrchestrator` class
- Pro: Better separation, focused responsibility
- Con: More files, need to wire it up

**Recommendation:** Start with Option A (add to AppController). Extract to EditOrchestrator if AppController exceeds 1500 lines.

### 2. How to Handle Progress Callbacks?

Edit/delete operations might benefit from progress indication (e.g., "Deleting 50 transactions: 25/50...").

**Option A:** Pass callback from UI to controller
```python
def delete_transactions(self, ids, progress_callback=None):
    for i, txn_id in enumerate(ids):
        if progress_callback:
            progress_callback(i+1, len(ids))
        delete(txn_id)
```

**Option B:** Return generator/async iterator
```python
async def delete_transactions(self, ids):
    for i, txn_id in enumerate(ids):
        await delete(txn_id)
        yield (i+1, len(ids), txn_id)  # UI can show progress
```

**Recommendation:** Option A for simplicity (callbacks optional, None for testing).

### 3. Session Renewal Strategy?

**Option A:** Keep per-operation retry methods (current)
- `_commit_with_retry()`
- `_delete_with_retry()`
- Add `_edit_with_retry()` etc.

**Option B:** Decorator pattern
```python
@with_session_renewal
async def delete_transaction(self, txn_id):
    return await self.backend.delete_transaction(txn_id)
```

**Option C:** Centralized SessionManager
```python
session_manager.execute_with_renewal(
    lambda: backend.delete_transaction(txn_id)
)
```

**Recommendation:** Option B (decorator) - clean, reusable, testable.

---

## Expected Outcomes

### After Phase 1 (Edit Orchestration)

**Code Changes:**
- app.py: ~500 lines removed (edit methods simplified)
- app_controller.py: ~300 lines added (edit logic extracted)
- New tests: ~400 lines (comprehensive edit testing)
- Net: ~200 lines removed, much better separation

**Test Coverage:**
- app_controller.py: 84% → 95%
- test coverage of edit workflows: 0% → 95%

**Maintainability:**
- Edit bugs: Easier to find and fix (isolated in controller)
- New edit features: Implement in controller (testable), wire up UI (simple)
- Alternative UIs: Can reuse controller edit logic directly

---

## Migration Path

### Week 1: Edit Context Determination
- Define EditContext dataclass
- Implement determine_edit_context()
- Write 10+ tests for context determination
- Use in one edit method (merchant) as proof of concept

### Week 2: Merchant Edit Extraction
- Extract edit_merchant_current_selection()
- Unify all merchant edit paths to use controller
- Remove duplicate code from app.py
- Write 10+ tests for merchant editing

### Week 3: Category Edit & Hide/Unhide
- Apply same pattern to category editing
- Extract toggle_hide_current_selection()
- Write tests
- Remove duplicate code

### Week 4: Multi-Select & Undo
- Extract multi-select logic
- Integrate undo/redo with state.py
- Write tests
- Cleanup and polish

---

## Success Criteria

After refactoring, we should be able to:

✅ **Test edit workflows without TUI:**
```python
def test_bulk_merchant_rename():
    controller = setup_controller()
    controller.state.view_mode = ViewMode.MERCHANT
    # ... set up data

    count = controller.edit_merchant_current_selection("Amazon")

    assert count == 50
```

✅ **Build alternative UIs easily:**
```python
# Web API endpoint
count = controller.edit_merchant_current_selection(new_name)
return {"success": True, "edits_queued": count}
```

✅ **Understand edit logic by reading one file:**
- All edit orchestration in app_controller.py
- app.py just shows modals and displays results

✅ **Add new edit features quickly:**
- Implement in controller (testable)
- Wire up UI (10 lines)
- Done!

---

## Risks & Mitigation

### Risk 1: Breaking Existing Functionality

**Mitigation:**
- Keep all existing tests passing during refactoring
- Incremental approach (one method at a time)
- Test manually after each change
- Use feature flags to toggle between old/new code during transition

### Risk 2: Increased Complexity (More Files/Classes)

**Mitigation:**
- Only extract when clear benefit (testability, reusability)
- Don't over-abstract
- Keep related logic together
- Clear naming conventions

### Risk 3: Time Investment vs Benefit

**Mitigation:**
- Start with highest-impact refactoring (edit orchestration)
- Measure progress (test coverage, lines of code in app.py)
- Stop if diminishing returns
- Phases 4-5 are optional

---

## Recommended Next Steps

1. **Review this plan** - Discuss priorities and approach
2. **Start Phase 1** - Edit context determination
3. **Write tests first** - Define desired controller API through tests
4. **Implement incrementally** - One method at a time
5. **Validate continuously** - All tests passing, manual testing

---

## Appendix: Current Code Organization

### app.py Structure
```
Lines 1-170: Imports, CSS, class definition
Lines 171-340: __init__ and initialization helpers
Lines 341-460: Data loading (credentials, cache, fetch)
Lines 461-710: initialize_data() - startup flow
Lines 711-820: UI helpers (save/restore position, refresh)
Lines 821-900: View switching actions
Lines 901-1000: Time navigation actions
Lines 1001-1100: Multi-select logic
Lines 1101-1680: Edit orchestration (LARGEST SECTION)
Lines 1681-1860: Hide/unhide & transaction details
Lines 1861-2000: Delete & go_back
Lines 2001-2150: Session management & retry logic
Lines 2151-2290: Commit workflow
Lines 2291-2480: Row selection, main(), launch functions
```

**Observation:** Lines 1101-1860 (760 lines) are primarily business logic that should be in the controller!

### app_controller.py Structure
```
Lines 1-90: Class definition, display helpers
Lines 91-270: refresh_view() and view preparation
Lines 271-420: View switching methods
Lines 421-540: Sort, time, search operations
Lines 541-620: Data access methods
Lines 621-720: Edit queueing helpers (good!)
Lines 721-800: Sort field cycling logic
Lines 801-880: Action hints generation
Lines 881-934: Commit result handling
```

**Observation:** Controller has good foundations but is missing the orchestration layer that determines WHAT to edit based on current view state.

---

## Conclusion

moneyflow has a solid foundation with good separation in many areas (data_manager, state, basic controller operations). The main opportunity is extracting the **edit/hide/delete orchestration logic** from app.py into testable controller methods.

**Recommended Focus:** Phase 1 (Edit Orchestration) - highest impact, enables comprehensive testing of the primary use case (editing transactions).

**Effort:** ~2-3 days for Phase 1, significant reduction in app.py complexity, major improvement in testability.

**Long-term Vision:** app.py becomes a thin UI layer (show modals, display results), with all business logic in controller (fully testable, reusable across UIs).
