# Refactoring Plan: Monarch PUI → Personal Finance PUI

## Goal
Transform from Monarch-specific tool to a generic Personal Finance Power User Interface where Monarch is just one supported backend.

## Rationale
- Avoid DMCA/trademark concerns
- Make it clear: NOT affiliated with Monarch Money
- Future extensibility for other finance platforms
- Monarch is just the first (and currently only) supported backend

## Proposed Names
- **Project**: `personal-finance-pui` or `finance-pui` (shorter)
- **Package**: `finance_pui`
- **Description**: "Personal Finance Power User Interface - keyboard-driven TUI for managing transactions"

## Architecture Changes

### 1. Backend Abstraction Layer

Create `finance_pui/backends/base.py`:
```python
class FinanceBackend(ABC):
    """Abstract base class for finance platform backends."""

    @abstractmethod
    async def login(...) -> None: ...

    @abstractmethod
    async def get_transactions(...) -> Dict: ...

    @abstractmethod
    async def update_transaction(...) -> Dict: ...

    # etc.
```

### 2. Monarch Implementation

Move to `finance_pui/backends/monarch.py`:
- Rename `monarchmoney.py` → `monarch.py`
- Add header: "Monarch Money backend implementation"
- Keep MonarchMoney class but wrap in MonarchBackend
- Keep attribution to hammem/monarchmoney

### 3. Demo Implementation

Move to `finance_pui/backends/demo.py`:
- Already separate, just needs new import path
- Update to use FinanceBackend base class

### 4. Backend Selection in Setup

Modify credential setup:
1. First screen: "Select your finance platform"
   - [ ] Monarch Money
   - [ ] Demo Mode (synthetic data)
   - [ ] Other (coming soon...)

2. Based on selection:
   - Monarch: Show Monarch-specific credential setup
   - Demo: Skip directly to app
   - Other: Show "not yet supported"

3. Store in credentials:
   ```json
   {
     "backend": "monarch",
     "backend_config": {
       "email": "...",
       "password": "...",
       "mfa_secret": "..."
     }
   }
   ```

### 5. Documentation Updates

**README.md**:
- Title: "Personal Finance Power User Interface"
- Subtitle: "A keyboard-driven TUI for managing personal finance transactions"
- Section: "Supported Platforms"
  - ✅ Monarch Money (full support)
  - 🚧 Others (coming soon)
- Clear disclaimer: "Not affiliated with Monarch Money, Inc."

**STATUS.md**:
- Update all references
- Add "Backend Support" section

**CLAUDE.md**:
- Update developer documentation
- Add "Adding New Backends" guide

## File Rename/Move Plan

```
monarch_pui/                        → finance_pui/
├── monarchmoney.py                 → backends/monarch.py
├── demo_backend.py                 → backends/demo.py
├── demo_data_generator.py          → backends/demo_data.py
├── (new) backends/base.py          → Abstract base class
├── (new) backends/__init__.py      → Backend registry
├── app.py                          → (update imports)
├── data_manager.py                 → (stays, works with any backend)
├── state.py                        → (stays, backend-agnostic)
├── credentials.py                  → (update to store backend type)
└── ...
```

## Migration Strategy

### Phase 1: Create Abstraction (Agents)
- Create FinanceBackend base class
- Create MonarchBackend wrapper
- Update DemoBackend to inherit from base

### Phase 2: Rename Project (Manual)
- monarch_pui → finance_pui (package)
- monarch-pui → finance-pui (project)
- Update all imports
- Update all tests

### Phase 3: Update Setup Flow (Agents)
- Add backend selection screen
- Update credential storage format
- Update app initialization

### Phase 4: Documentation (Manual)
- README: Emphasize general-purpose, Monarch is one backend
- Add disclaimer: Not affiliated with Monarch Money
- Update all references

### Phase 5: Testing (Agents)
- Verify all 331 tests still pass
- Add backend selection tests
- Add backend abstraction tests

## Estimated Scope
- Files to modify: ~30
- New files: ~5
- Tests to update: ~50
- Documentation: ~5 files
- Estimated time: 2-3 hours with agents

## Risks
- Breaking existing tests
- Import path hell
- Credential migration for existing users
- Missing edge cases

## Mitigation
- Use agents for mechanical changes
- Comprehensive testing after each phase
- Clear commit messages
- Can roll back if issues

## Ready to Execute?

This plan provides a thorough roadmap. Should I proceed with execution using agents for the heavy lifting?
