# Session Management Refactoring Plan

**Problem:** Session/auth logic scattered in 3+ places in app.py, all with identical patterns.

## Current Duplication:

### The Pattern (appears 3 times):
```python
self.mm.delete_session()
await self.mm.login(
    email=creds["email"],
    password=creds["password"],
    use_saved_session=False,  # Force fresh login
    save_session=True,
    mfa_secret_key=creds["mfa_secret"]
)
```

### Locations:
1. **_login_with_retry** (lines 408-417) - Initial login with stale session
2. **_fetch_data_with_retry** (lines 557-565) - Session expired during fetch
3. **_refresh_session** (lines 1572-1580) - Session expired during commit

Each was added to fix a specific bug. All are critical.

## Phase 1: Conservative Consolidation (SAFE)

### Extract common helper in app.py:

```python
async def _do_fresh_login(self, creds_or_stored):
    """
    Perform fresh login after deleting stale session.

    This is the common pattern used in 3 places. Extracted to avoid duplication
    while keeping the logic exactly as it evolved through bug fixes.

    Args:
        creds_or_stored: Either creds dict or self.stored_credentials

    Returns:
        None (raises on failure)
    """
    self.mm.delete_session()
    await self.mm.login(
        email=creds_or_stored["email"],
        password=creds_or_stored["password"],
        use_saved_session=False,  # Force fresh login
        save_session=True,
        mfa_secret_key=creds_or_stored["mfa_secret"]
    )
```

### Then use it everywhere:
```python
# In _login_with_retry:
await self._do_fresh_login(creds)

# In _fetch_data_with_retry:
await self._do_fresh_login(creds)

# In _refresh_session:
await self._do_fresh_login(self.stored_credentials)
```

**Benefits:**
- Consolidates the 3-line pattern
- No logic changes (just extraction)
- Easy to test
- Low risk

## Phase 2: Rename mm → backend (SAFE)

Simple find/replace:
- `self.mm` → `self.backend`
- Update all 20+ references

**Benefits:**
- Generic naming (not MonarchMoney-specific)
- No logic changes
- Low risk

## Phase 3: SessionManager (FUTURE - Requires More Thought)

Create `moneyflow/session_manager.py`:

```python
class SessionManager:
    """
    Manages backend authentication and session lifecycle.

    Encapsulates:
    - Login with retry (including stale session detection)
    - Session refresh
    - Credential storage
    """

    def __init__(self, backend):
        self.backend = backend
        self.credentials = None

    async def login_with_retry(self, creds, on_retry_callback, loading_status):
        """Login with automatic retry and stale session handling."""
        # Move _login_with_retry logic here

    async def refresh_session(self, on_notification=None):
        """Refresh expired session."""
        # Move _refresh_session logic here

    async def ensure_authenticated_for_operation(self, operation, creds=None):
        """
        Wrap an operation with automatic session refresh on 401.

        Usage:
            result = await session_manager.ensure_authenticated_for_operation(
                lambda: self.data_manager.fetch_all_data(...)
            )
        """
        # Wraps operation, catches 401, refreshes, retries
```

**Benefits:**
- All session logic in one place
- Testable without app context
- Clean separation

**Risks:**
- More complex (wrapping operations)
- Need to preserve all error handling
- Need comprehensive tests before migrating

## Recommendation for Next Session:

**Do Phase 1 now (30 min):**
- Extract `_do_fresh_login()` helper
- Replace 3 duplicated blocks
- Test thoroughly

**Do Phase 2 soon (15 min):**
- Rename mm → backend
- Update references
- Test

**Consider Phase 3 later (2-3 hours):**
- Create SessionManager
- Write comprehensive tests
- Migrate carefully
- Only after Phases 1 & 2 are stable

## Why Be Careful:

Each session refresh call was added to fix:
1. "Invalid token" error on cached sessions
2. 401 during data fetch (session expired between login and fetch)
3. 401 during commit (long-running sessions)

Breaking any of these would cause hard-to-debug auth loops.

**Conservative approach: Extract the common pattern first, then consider bigger refactoring.**
