# File Organization Analysis

**Date**: 2025-10-14
**Current Files**: 32 Python modules
**Status**: Proposed reorganization for better intuitiveness

## Current Organization

```
moneyflow/
├── app.py (1000 lines) - Main Textual TUI application
├── state.py - Application state management
├── data_manager.py - Data operations with Polars
├── credentials.py - Encrypted credential storage
├── cache_manager.py - Parquet caching
├── retry_logic.py - Retry with exponential backoff
├── notification_helper.py - UI notification messages
├── modal_helper.py - Modal parameter preparation
├── view_presenter.py - View formatting (pure functions)
├── time_navigator.py - Date calculations (pure functions)
├── commit_orchestrator.py - DataFrame updates (pure functions)
├── duplicate_detector.py - Duplicate detection logic
├── monarchmoney.py - MonarchMoney GraphQL client (external)
├── demo_data_generator.py - Synthetic transaction data
├── keybindings.py - Keyboard binding documentation (UNUSED)
├── logging_config.py - Logging configuration
├── backends/
│   ├── base.py - FinanceBackend ABC
│   ├── monarch.py - MonarchBackend implementation
│   └── demo.py - DemoBackend implementation
├── screens/
│   ├── credential_screens.py - Login, unlock, filters, quit modals
│   ├── edit_screens.py - Edit merchant, category, delete modals
│   ├── review_screen.py - Review changes before commit
│   ├── search_screen.py - Search modal
│   ├── transaction_detail_screen.py - Transaction info modal
│   └── duplicates_screen.py - Duplicate transaction screen
└── widgets/
    └── help_screen.py - Help modal
```

## Problems with Current Organization

### 1. **Flat Structure**
- 18 files in root `moneyflow/` directory
- Hard to see logical grouping
- Business logic mixed with utilities

### 2. **Unclear Names**
- `view_presenter.py` - sounds like UI, but it's pure business logic
- `commit_orchestrator.py` - what does "orchestrator" mean?
- `keybindings.py` - seems important, actually unused
- `modal_helper.py` / `notification_helper.py` - similar names, related purpose

### 3. **Empty Directories**
- `moneyflow/views/` - exists but has no real content

### 4. **Inconsistent Grouping**
- UI helpers (`notification_helper`, `modal_helper`) at root level
- Screen modals organized under `screens/`
- Pure functions (`time_navigator`, `view_presenter`) at root level

## Proposed Reorganization

### Option A: Organize by Layer (Recommended)

```
moneyflow/
├── app.py - Main entry point (keep at root for visibility)
├── core/  ← NEW: Business logic layer
│   ├── state.py
│   ├── data_manager.py
│   ├── formatters.py (was: view_presenter.py)
│   ├── date_utils.py (was: time_navigator.py)
│   ├── commit.py (was: commit_orchestrator.py)
│   └── duplicates.py (was: duplicate_detector.py)
├── backends/
│   ├── base.py
│   ├── monarch.py
│   ├── demo.py
│   └── demo_data.py (was: demo_data_generator.py)
├── ui/  ← NEW: All UI-related code
│   ├── notifications.py (was: notification_helper.py)
│   ├── modals.py (was: modal_helper.py)
│   ├── screens/
│   │   ├── credentials.py (was: credential_screens.py)
│   │   ├── editing.py (was: edit_screens.py)
│   │   ├── review.py (was: review_screen.py)
│   │   ├── search.py (was: search_screen.py)
│   │   ├── transaction_detail.py (was: transaction_detail_screen.py)
│   │   ├── duplicates.py (was: duplicates_screen.py)
│   │   └── help.py (was: widgets/help_screen.py)
│   └── (empty widgets/ removed)
├── infrastructure/  ← NEW: Cross-cutting concerns
│   ├── credentials.py
│   ├── cache.py (was: cache_manager.py)
│   ├── retry.py (was: retry_logic.py)
│   └── logging.py (was: logging_config.py)
└── monarchmoney.py (keep separate for upstream diffs)
```

### Option B: Organize by Feature (Alternative)

```
moneyflow/
├── app.py
├── transactions/  ← Transaction-related logic
│   ├── state.py
│   ├── data_manager.py
│   ├── duplicates.py
│   └── formatters.py
├── editing/  ← Edit workflows
│   ├── commit.py
│   ├── screens/
│   │   ├── edit_merchant.py
│   │   ├── edit_category.py
│   │   └── review.py
│   └── modals.py
├── navigation/  ← View navigation
│   ├── time.py (date_utils)
│   └── screens/
│       └── search.py
├── auth/  ← Authentication
│   ├── credentials.py
│   ├── backends/
│   │   ├── base.py
│   │   ├── monarch.py
│   │   └── demo.py
│   └── screens/
│       └── credentials.py
└── ... (rest)
```

## Recommendation: Option A (Organize by Layer)

**Why Layer-based is better:**
1. ✅ Matches the existing architecture (already have backend/, screens/ layers)
2. ✅ Clear separation between business logic and UI
3. ✅ Easier to find files ("where's the date math?" → `core/date_utils.py`)
4. ✅ Supports future refactoring to IViewPresenter pattern
5. ✅ Standard pattern in well-organized codebases

**Why NOT Feature-based:**
- Creates too many small directories
- Some features span multiple layers (editing touches core, UI, backends)
- Harder to enforce architectural boundaries

## Specific Recommendations

### Rename Files for Clarity

**Pure Function Modules** (these are misleadingly named):
- `view_presenter.py` → `formatters.py` or `core/formatters.py`
  - **Why**: It doesn't "present" anything, it formats data for display
  - Contains: `format_currency()`, `compute_flags()`, `prepare_*_view()`

- `time_navigator.py` → `date_utils.py` or `core/date_utils.py`
  - **Why**: "Navigator" sounds like UI navigation, but it's pure date math
  - Contains: `get_month_range()`, `previous_period()`, `next_period()`

- `commit_orchestrator.py` → `commit.py` or `core/commit.py`
  - **Why**: "Orchestrator" is vague, and the file just applies edits
  - Contains: `apply_edit_to_dataframe()`, `apply_edits_to_dataframe()`

**Helper Modules** (move to subdirectory):
- `notification_helper.py` → `ui/notifications.py`
- `modal_helper.py` → `ui/modals.py`
- `retry_logic.py` → `infrastructure/retry.py` or `utils/retry.py`

**Manager Modules** (clarify purpose):
- `cache_manager.py` → `infrastructure/cache.py` or keep as-is
- `data_manager.py` → stays at root or `core/data.py`

### Delete Unused Files

- `keybindings.py` - Documentation only, never imported (DELETE)
- `moneyflow/views/__init__.py` - Empty directory (DELETE)
- `moneyflow/widgets/__init__.py` - Nearly empty (CONSOLIDATE into screens/)

### Consolidate Related Files

**Option 1: Merge helpers into a `ui/` package**
```
ui/
├── __init__.py
├── notifications.py (all notification messages)
├── modals.py (all modal parameters)
└── screens/ (all modal screens)
```

**Option 2: Merge pure functions into a `core/` package**
```
core/
├── __init__.py
├── state.py
├── data.py (was: data_manager.py)
├── formatters.py (was: view_presenter.py)
├── dates.py (was: time_navigator.py)
├── commit.py (was: commit_orchestrator.py)
└── duplicates.py (was: duplicate_detector.py)
```

## Migration Strategy (If You Decide to Reorganize)

### Phase 1: Rename for Clarity (Low Risk - 1 hour)
1. Rename `view_presenter.py` → `formatters.py`
2. Rename `time_navigator.py` → `date_utils.py`
3. Rename `commit_orchestrator.py` → `commit_utils.py`
4. Update imports in `app.py` and tests
5. Run tests to verify

### Phase 2: Create `core/` Package (Medium Risk - 2 hours)
1. Create `moneyflow/core/` directory
2. Move: `state.py`, `data_manager.py`, `formatters.py`, `date_utils.py`, `commit_utils.py`, `duplicate_detector.py`
3. Update all imports
4. Run tests

### Phase 3: Create `ui/` Package (Low Risk - 1 hour)
1. Create `moneyflow/ui/` directory
2. Move: `notification_helper.py` → `ui/notifications.py`
3. Move: `modal_helper.py` → `ui/modals.py`
4. Merge `widgets/` into `screens/`
5. Update imports
6. Run tests

### Phase 4: Create `infrastructure/` Package (Low Risk - 1 hour)
1. Create `moneyflow/infrastructure/`
2. Move: `credentials.py`, `cache_manager.py`, `retry_logic.py`, `logging_config.py`
3. Update imports
4. Run tests

### Phase 5: Cleanup (Low Risk - 30 min)
1. Delete `keybindings.py`
2. Delete empty `views/` directory
3. Update CLAUDE.md with new structure
4. Update README if it references file paths

**Total Effort**: ~5-6 hours
**Risk**: Low (imports can be updated mechanically, tests catch breakage)

## Recommendation

**Do it NOW if:**
- You're onboarding contributors soon
- You plan major features that will add more files
- The current structure is bothering you

**Wait if:**
- You're focused on features/docs
- Current organization is "good enough"
- Don't want to spend half a day on file shuffling

**My Opinion**: The current organization is functional. The new helpers (`notification_helper`, `modal_helper`) are well-named and their purpose is clear. The only real issues are:

1. **`view_presenter.py`** - misleading name (should be `formatters.py`)
2. **`keybindings.py`** - unused, should be deleted
3. **Root directory clutter** - 18 files is a lot

**Minimal Action** (30 minutes):
- Rename `view_presenter.py` → `formatters.py`
- Delete `keybindings.py` and `views/` directory
- Leave everything else as-is

This gives you 80% of the clarity benefit with minimal effort.
