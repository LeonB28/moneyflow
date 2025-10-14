# Session Handoff - Session Management Refactoring

## Current State (All Tests Pass):
- **577 tests pass** ✅
- **72% coverage**
- **All features working**
- Ready for session management cleanup

## IMMEDIATE TASK: Session Management Refactoring

### Problem:
Session refresh logic duplicated in 3 places (lines 408, 557, 1572):
```python
self.mm.delete_session()
await self.mm.login(email, password, use_saved_session=False, ...)
```

Each was carefully added to fix specific bugs:
1. Invalid token on cached sessions
2. 401 during data fetch
3. 401 during commit

### Solution - Phase 1 (Do NOW):

**Step 1:** Extract common pattern to helper:
```python
async def _do_fresh_login(self, creds):
    """Delete stale session and perform fresh login."""
    self.mm.delete_session()
    await self.mm.login(
        email=creds["email"],
        password=creds["password"],
        use_saved_session=False,
        save_session=True,
        mfa_secret_key=creds["mfa_secret"]
    )
```

**Step 2:** Replace 3 duplicated blocks with calls to helper

**Step 3:** Test thoroughly - verify no auth regressions

### Solution - Phase 2 (Do NEXT):

**Rename mm → backend** throughout app.py:
- `self.mm` → `self.backend`
- 20+ references to update
- Generic naming (not MonarchMoney-specific)

### Files to Modify:
- `/Users/wesm/code/moneyflow/moneyflow/app.py` (lines 173, 175, 250, 393, 408, 410, 557, 559, 632, 704, 1536, 1572, 1574)
- Run: `grep -n "self.mm" moneyflow/app.py` to find all references

### Testing Checklist:
- [ ] All 577 tests still pass
- [ ] No new auth errors in logs
- [ ] Login works
- [ ] Data fetch works
- [ ] Commit works
- [ ] Session refresh works on 401

## Recent Accomplishments (Don't Lose):

1. ✅ MVP pattern implemented (IViewPresenter, AppController, TextualView)
2. ✅ initialize_data refactored (391 → 91 lines)
3. ✅ Commit handling extracted (data corruption bug provably fixed)
4. ✅ 30 new tests added
5. ✅ 844 lines of code deleted

## Key Files:
- `moneyflow/app.py` - Main TUI (1859 lines)
- `moneyflow/app_controller.py` - Business logic (336 lines)
- `moneyflow/textual_view.py` - Rendering (87 lines)
- `moneyflow/view_interface.py` - Interface (86 lines)
- `tests/test_app_controller.py` - Controller tests (30 tests)
- `tests/mock_view.py` - Test infrastructure

## Architecture:
```
MoneyflowTUI (app.py)
  ↓ delegates
AppController (app_controller.py)
  ↓ uses
IViewPresenter (view_interface.py)
  ↓ implemented by
TextualViewPresenter (textual_view.py)
```

## Safe to Delete After Migration:
- This file (NEXT_SESSION_HANDOFF.md)
- SESSION_MANAGEMENT_REFACTOR.md (merge into this)
