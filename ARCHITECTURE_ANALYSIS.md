# Architecture Analysis: Decoupling from Textual UI

**Date**: 2025-10-14
**Status**: Planning / Analysis
**Goal**: Enable better testing and alternative UI implementations (web, GUI, etc.)

## Current State Analysis

### Coupling Metrics

**Textual API dependencies in `app.py`:**
- `self.notify()`: 46 calls - User notifications
- `self.push_screen()`: 21 calls - Modal dialogs
- `self.query_one()`: 27 calls - Widget access
- `self.run_worker()`: 10 calls - Async tasks
- `self.exit()`: 6 calls - Application termination

**Total Textual coupling points**: 110+ direct API calls

**Code organization:**
- 35 action methods (keyboard bindings → business logic)
- 15 helper methods (mix of business logic + UI updates)
- 11 UI update methods (pure view rendering)

### Current Architecture (Layered)

```
┌─────────────────────────────────────────────────────┐
│  moneyflow/app.py (MoneyflowTUI)                   │
│  ├─ Textual.App subclass                           │
│  ├─ Keyboard bindings (BINDINGS)                   │
│  ├─ Action handlers (action_*)                     │
│  ├─ UI updates (update_*, show_*, refresh_*)       │
│  └─ Business logic (mixed in with above)           │
└─────────────────────────────────────────────────────┘
              ↓ uses
┌─────────────────────────────────────────────────────┐
│  Business Logic Modules (GOOD SEPARATION)          │
│  ├─ state.py         (AppState)                    │
│  ├─ data_manager.py  (DataManager)                 │
│  ├─ view_presenter.py (ViewPresenter)              │
│  ├─ time_navigator.py (TimeNavigator)              │
│  ├─ commit_orchestrator.py (CommitOrchestrator)    │
│  └─ retry_logic.py   (retry_with_backoff)          │
└─────────────────────────────────────────────────────┘
              ↓ uses
┌─────────────────────────────────────────────────────┐
│  Backend Abstraction (EXCELLENT SEPARATION)        │
│  ├─ backends/base.py (FinanceBackend ABC)          │
│  ├─ backends/monarch.py (MonarchBackend)           │
│  └─ backends/demo.py (DemoBackend)                 │
└─────────────────────────────────────────────────────┘
```

### What's Already Decoupled (✅ Good Architecture)

1. **Backend abstraction**: `FinanceBackend` ABC allows swapping Monarch/Demo/YNAB
2. **Business logic**: ViewPresenter, TimeNavigator, CommitOrchestrator are pure functions
3. **State management**: `AppState` is UI-agnostic (just data structures)
4. **Data operations**: `DataManager` uses Polars, no UI dependencies

### What's Tightly Coupled (❌ Needs Refactoring)

1. **Notification system**: 46 calls to `self.notify()` scattered everywhere
2. **Modal dialogs**: 21 calls to `push_screen()` for user input
3. **Widget access**: 27 calls to `query_one()` for DOM manipulation
4. **Async orchestration**: `run_worker()` is Textual-specific
5. **Mixed responsibilities**: Action handlers contain UI + business logic

## Problems with Current Architecture

### 1. **Testing Challenges**
- Cannot test notification UX without running full Textual app
- Modal interactions require complex Textual pilot setup
- UI state changes buried in action handlers
- Business logic decisions hidden behind UI method calls

**Example of the problem:**
```python
async def _commit_with_retry(self, edits):
    # Business logic decision
    if auth_error:
        # UI call tightly coupled
        self.notify("Session expired during commit. Refreshing...", timeout=2)
        # More business logic
        if await self._refresh_session():
            # Another UI call
            self.notify("Session refreshed successfully", ...)
```

### 2. **Alternative UI Implementation is Hard**
Want to build a web UI? You'd need to:
- Rewrite all 46 notification calls
- Rewrite all 21 modal dialog flows
- Rewrite widget access patterns
- Handle async differently (no `run_worker`)

### 3. **Business Logic is Obscured**
Looking at an action handler, hard to tell:
- What's the core business logic?
- What's just UI feedback?
- What side effects happen?

## Proposed Target Architecture

### Model-View-Presenter (MVP) Pattern

```
┌──────────────────────────────────────────────────────────────┐
│  UI Layer (Pluggable)                                        │
│  ├─ textual_ui/                                              │
│  │   ├─ textual_app.py (MoneyflowTextualUI)                 │
│  │   ├─ textual_presenter.py (implements IViewPresenter)    │
│  │   └─ screens/ (Textual-specific modals)                  │
│  ├─ web_ui/ (FUTURE)                                         │
│  │   ├─ flask_app.py (MoneyflowWebUI)                       │
│  │   └─ web_presenter.py (implements IViewPresenter)        │
│  └─ gui_ui/ (FUTURE)                                         │
│      └─ qt_app.py (MoneyflowQtUI)                           │
└──────────────────────────────────────────────────────────────┘
                        ↓ implements
┌──────────────────────────────────────────────────────────────┐
│  View Contract (Abstract Base Classes)                       │
│  ├─ IViewPresenter (ABC)                                     │
│  │   ├─ show_notification(message, severity, timeout)       │
│  │   ├─ show_modal(modal_type, **params) → result           │
│  │   ├─ update_data_table(view_data)                        │
│  │   ├─ update_breadcrumb(text)                             │
│  │   ├─ update_stats(stats_dict)                            │
│  │   └─ update_hints(hints_text)                            │
│  └─ IModalResult (protocols for typed modal results)         │
└──────────────────────────────────────────────────────────────┘
                        ↓ used by
┌──────────────────────────────────────────────────────────────┐
│  Application Controller (UI-agnostic)                        │
│  ├─ controller/app_controller.py                             │
│  │   ├─ AppController(view: IViewPresenter, ...)            │
│  │   ├─ action_commit_changes()                             │
│  │   ├─ action_edit_merchant()                              │
│  │   ├─ action_navigate_back()                              │
│  │   └─ ... (all business logic)                            │
│  └─ Uses existing modules:                                   │
│      ├─ state.py, data_manager.py                           │
│      ├─ view_presenter.py (data formatting)                 │
│      └─ retry_logic.py, etc.                                │
└──────────────────────────────────────────────────────────────┘
```

### Key Abstraction: IViewPresenter

```python
from abc import ABC, abstractmethod
from typing import Any, Optional, Dict
from enum import Enum

class NotificationSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

class ModalType(Enum):
    EDIT_MERCHANT = "edit_merchant"
    SELECT_CATEGORY = "select_category"
    CONFIRM_DELETE = "confirm_delete"
    REVIEW_CHANGES = "review_changes"
    # ... etc

class IViewPresenter(ABC):
    """Abstract interface for UI presentation."""

    @abstractmethod
    def show_notification(
        self,
        message: str,
        severity: NotificationSeverity = NotificationSeverity.INFO,
        timeout: int = 3
    ) -> None:
        """Show a notification to the user."""
        pass

    @abstractmethod
    async def show_modal(
        self,
        modal_type: ModalType,
        **params
    ) -> Any:
        """
        Show a modal dialog and return user's choice.

        Returns:
            Result depends on modal_type:
            - EDIT_MERCHANT: Optional[str] (new merchant name or None)
            - SELECT_CATEGORY: Optional[str] (category_id or None)
            - CONFIRM_DELETE: bool
            - REVIEW_CHANGES: bool
        """
        pass

    @abstractmethod
    def update_data_table(self, view_data: Dict[str, Any]) -> None:
        """
        Update the main data table.

        Args:
            view_data: {
                "columns": [...],
                "rows": [...],
                "cursor_position": int
            }
        """
        pass

    @abstractmethod
    def update_breadcrumb(self, text: str) -> None:
        """Update navigation breadcrumb."""
        pass

    @abstractmethod
    def update_stats(self, stats: Dict[str, Any]) -> None:
        """
        Update statistics display.

        Args:
            stats: {
                "txn_count": int,
                "income": float,
                "expenses": float,
                "savings": float
            }
        """
        pass

    @abstractmethod
    def update_action_hints(self, hints: str) -> None:
        """Update action hints bar."""
        pass

    @abstractmethod
    def exit_app(self) -> None:
        """Exit the application."""
        pass
```

### Refactored AppController

```python
class AppController:
    """
    UI-agnostic application controller.

    Contains all business logic, delegates all UI operations to view.
    """

    def __init__(
        self,
        view: IViewPresenter,
        backend: FinanceBackend,
        state: AppState,
        data_manager: DataManager
    ):
        self.view = view
        self.backend = backend
        self.state = state
        self.data_manager = data_manager

    async def action_commit_changes(self) -> None:
        """Commit pending changes (business logic only)."""
        # Check if there are changes
        pending_count = len(self.data_manager.pending_edits)
        if pending_count == 0:
            self.view.show_notification("No pending changes to commit", timeout=2)
            return

        # Show review modal (view handles UI)
        should_commit = await self.view.show_modal(
            ModalType.REVIEW_CHANGES,
            edits=self.data_manager.pending_edits,
            categories=self.data_manager.categories
        )

        if not should_commit:
            return

        # Commit with retry logic (business logic)
        self.view.show_notification(f"Committing {pending_count} change(s)...", timeout=2)

        try:
            success, failure = await self._commit_with_retry(self.data_manager.pending_edits)

            if failure > 0:
                self.view.show_notification(
                    f"✅ Saved {success}, ❌ {failure} failed",
                    severity=NotificationSeverity.WARNING,
                    timeout=5
                )
            else:
                self.view.show_notification(
                    f"✅ Committed {success} change(s)!",
                    severity=NotificationSeverity.INFO,
                    timeout=3
                )

            # Update local state (business logic)
            self._apply_edits_locally()
            self.data_manager.pending_edits.clear()

            # Refresh view (view handles rendering)
            self.refresh_current_view()

        except RetryAborted:
            self.view.show_notification("Commit cancelled by user",
                                       severity=NotificationSeverity.WARNING,
                                       timeout=3)
        except Exception as e:
            self.view.show_notification(f"❌ Error: {e}",
                                       severity=NotificationSeverity.ERROR,
                                       timeout=5)

    def refresh_current_view(self) -> None:
        """Refresh all UI components based on current state."""
        # Prepare view data (pure business logic)
        view_data = self._prepare_view_data()

        # Delegate rendering to view
        self.view.update_data_table(view_data)
        self.view.update_breadcrumb(self.state.get_breadcrumb())
        self.view.update_stats(self._calculate_stats())
        self.view.update_action_hints(self._get_current_hints())
```

## Migration Strategy

### Phase 1: Extract View Interface (Low Risk)
**Goal**: Define `IViewPresenter` without changing existing code

1. Create `moneyflow/ui/view_interface.py` with ABC
2. Create `moneyflow/ui/textual_presenter.py` that wraps current app
3. No functional changes, just organizational

**Effort**: 2-3 hours
**Risk**: Low (no behavior changes)

### Phase 2: Create AppController (Medium Risk)
**Goal**: Extract business logic from MoneyflowTUI

1. Create `moneyflow/controller/app_controller.py`
2. Move action handlers one-by-one:
   - Start with simple actions (quit, navigate)
   - Then complex actions (commit, edit)
3. MoneyflowTUI becomes thin wrapper that:
   - Handles keyboard bindings
   - Delegates to AppController
   - Implements IViewPresenter

**Effort**: 1-2 weeks
**Risk**: Medium (need careful testing at each step)

### Phase 3: Add Controller Tests (Low Risk)
**Goal**: Test business logic without UI

1. Create `MockViewPresenter` for testing
2. Write tests for AppController actions
3. Verify notification sequences
4. Test modal flows

**Effort**: 3-5 days
**Risk**: Low (pure testing)

**Example test:**
```python
class MockViewPresenter(IViewPresenter):
    def __init__(self):
        self.notifications = []
        self.modals_shown = []

    def show_notification(self, message, severity, timeout):
        self.notifications.append((message, severity, timeout))

    async def show_modal(self, modal_type, **params):
        self.modals_shown.append((modal_type, params))
        # Return mock result based on test scenario
        return True

async def test_commit_with_retry_shows_notifications():
    """Test that retry logic shows correct notification sequence."""
    view = MockViewPresenter()
    controller = AppController(view, mock_backend, state, data_manager)

    # Simulate commit that fails then succeeds
    await controller.action_commit_changes()

    # Verify notification sequence
    assert len(view.notifications) == 3
    assert "Session expired" in view.notifications[0][0]
    assert "Retrying" in view.notifications[1][0]
    assert "✅ Committed" in view.notifications[2][0]
```

### Phase 4: Alternative UI (Optional Future)
**Goal**: Prove architecture works with different UI

Could implement:
- **Web UI**: Flask/FastAPI + HTMX + WebSockets
- **GUI**: Qt/GTK application
- **API**: REST API for mobile apps

## Benefits of Refactoring

### 1. **Testability** ✅
- Test business logic without UI
- Verify notification sequences programmatically
- Test modal flows with mocks
- No more manual QA for retry logic

### 2. **Clarity** ✅
- Clear separation: Controller = business logic, View = presentation
- Easy to see what an action DOES vs what it SHOWS
- Type hints make contracts explicit

### 3. **Flexibility** ✅
- Swap UIs without touching business logic
- A/B test different notification strategies
- Add telemetry/analytics easily

### 4. **Maintainability** ✅
- Changes to Textual API isolated to one place
- Business logic changes don't require UI updates
- Easier onboarding for contributors

## Risks & Mitigations

### Risk 1: Over-abstraction
**Risk**: Create complex interfaces that don't fit all UIs
**Mitigation**: Start with Textual-only, evolve interface organically

### Risk 2: Breaking existing functionality
**Risk**: Refactoring introduces bugs
**Mitigation**:
- Incremental migration (one action at a time)
- Keep existing tests passing
- Add controller tests BEFORE migrating

### Risk 3: Async complexity
**Risk**: Modal flows are async, hard to abstract
**Mitigation**: Use `async def show_modal()` in interface, let each UI handle it

## Recommendation

**I recommend Phase 1 + Phase 2 + Phase 3 as a future milestone**, but NOT immediately.

**Why wait?**
1. Current architecture is "good enough" for now
2. Business logic modules already well-separated
3. Tests cover critical paths
4. No immediate need for alternative UI

**When to do it?**
- When you decide to build a web UI
- When Textual testing becomes critical
- When onboarding contributors who find current structure confusing
- When you have 2-3 weeks for focused refactoring

**What to do NOW:**
1. Keep this analysis document for future reference
2. When adding new features, try to keep business logic in helper methods
3. Avoid adding more direct `self.notify()` calls - use a helper instead
4. Document major user flows (like commit with retry)

## Alternative: Incremental Improvement (Recommended for Now)

Instead of big refactoring, make small improvements:

### 1. **Notification Helper** (1 hour)
```python
class NotificationHelper:
    """Centralized notification logic."""

    @staticmethod
    def commit_starting(count: int) -> tuple[str, str, int]:
        return (f"Committing {count} change(s)...", "info", 2)

    @staticmethod
    def session_expired() -> tuple[str, str, int]:
        return ("Session expired during commit. Refreshing...", "warning", 2)

    @staticmethod
    def retry_waiting(attempt: int, wait_seconds: float) -> tuple[str, str, int]:
        return (
            f"⚠ Retrying commit in {wait_seconds:.0f}s (attempt {attempt + 1}/5). Press Ctrl-C to abort.",
            "warning",
            int(wait_seconds)
        )

# Usage:
msg, severity, timeout = NotificationHelper.session_expired()
self.notify(msg, severity=severity, timeout=timeout)
```

Benefits: Testable notification messages, consistent wording, easy to change

### 2. **Extract Modal Logic** (2 hours)
Create helper methods that return modal parameters:
```python
def _get_edit_merchant_params(self, merchant: str, count: int):
    """Get parameters for edit merchant modal (testable!)."""
    return {
        "merchant_name": merchant,
        "transaction_count": count,
        "all_merchants": self.data_manager.df["merchant"].unique().to_list()
    }

# Then in action handler:
params = self._get_edit_merchant_params(merchant, count)
result = await self.push_screen(EditMerchantScreen(**params), wait_for_dismiss=True)
```

Benefits: Can test modal parameters without UI

## Conclusion

The current architecture is **functionally good** but **structurally coupled to Textual**. A full MVP refactoring would enable:
- Comprehensive UI testing
- Alternative UI implementations
- Clearer separation of concerns

However, it's a **significant effort** (2-3 weeks) and should be done when:
- You have time for focused refactoring
- You plan to build an alternative UI
- Testing the exact notification UX becomes critical

For now, **incremental improvements** (notification helper, modal parameter extraction) provide 80% of the testability benefits for 20% of the effort.
