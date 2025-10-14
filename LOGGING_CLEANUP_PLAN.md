# Logging Cleanup Plan

## Problems Identified

1. **Logging appears over Textual UI** - StreamHandler always writes to stderr
2. **57 debug print() statements** interfere with TUI presentation
3. **No retry logic for data fetch** - fails immediately on mobile internet
4. **Errors not logged during fetch** - "Failed to load data" with no details in log file

## Solution

### 1. Fix logging_config.py
- ✅ DONE: Add `console_output` parameter (default False)
- ✅ DONE: Only add StreamHandler when console_output=True
- TODO: Call `setup_logging(console_output=args.dev)` in main()

### 2. Remove debug print() statements
**57 print statements to remove:**
- `__init__`: 3 prints
- `compose`: 5 prints
- `on_mount`: 3 prints
- `initialize_data`: 20+ prints
- `action_quit_app`: 2 prints
- `main()`: 10+ prints

**Keep these:**
- Fatal error handler (lines 2025-2031) - user needs to see crash
- Initial "Logging to:" message (already in logging_config.py)

### 3. Add retry to data fetch
Wrap `fetch_all_data()` call in `retry_with_backoff`:
- Same pattern as login and commit
- Show "⚠ Data fetch failed. Retrying in 60s..."
- Log all failures with stack traces
- Handle network timeouts, GraphQL errors, etc.

### 4. Add logging to data_manager.fetch_all_data()
Currently fetch_all_data() doesn't log errors - just raises.
Need to log:
- Start of fetch
- Each batch fetched
- Errors during fetch (with exc_info=True)

## Implementation Order

1. Add logging setup after args parsing ✅
2. Add retry to data fetch (highest priority - fixes mobile issue)
3. Remove all debug prints (makes UI professional)
4. Test on --dev mode (prints should appear)
5. Test normal mode (no prints, clean UI)
