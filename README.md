# moneyflow

**Track your moneyflow from the terminal.**

A keyboard-driven terminal UI for managing personal finance transactions. Built for users who prefer efficiency and direct control over their financial data.

**Supported Platforms:**
- ✅ **Monarch Money** (full support)
- ✅ **Amazon Purchases** (import and analyze purchase history)
- ✅ **Demo Mode** (synthetic data for testing)
- 🚧 Other platforms (YNAB, Lunch Money - planned)

**Disclaimer**: Independent open-source project. Not affiliated with or endorsed by Monarch Money, Inc.

## Installation

### From PyPI (recommended)
```bash
# Install globally
pip install moneyflow

# Or use with uvx (no installation needed!)
uvx moneyflow

# Or use with pipx
pipx install moneyflow
```

### From Source
```bash
git clone https://github.com/wesm/moneyflow.git
cd moneyflow
uv sync
uv run moneyflow
```

## Quick Start

```bash
# Try demo mode first (no account needed!)
moneyflow --demo

# Connect your Monarch Money account
moneyflow

# Analyze your Amazon purchase history
moneyflow amazon import ~/Downloads/amazon-purchases.csv
moneyflow amazon

# Load only recent data for faster startup
moneyflow --year 2025
```

## Features

- **Keyboard-driven**: Vim-inspired navigation (hjkl, Enter to drill down, Esc to go back)
- **Aggregated views**: Group by merchant, category, or account
- **Bulk editing**: Multi-select with Space and batch update merchant names or categories
- **Type-to-search**: Filter as you type
- **Offline-first**: Download once, edit locally, commit changes when ready
- **Time navigation**: Switch between months and years with arrow keys
- **Review before commit**: Preview all changes before syncing
- **Encrypted credentials**: AES-128 encryption with PBKDF2 key derivation (100,000 iterations)
- **Pluggable backends**: Extensible architecture for multiple platforms

## Supported Platforms

### Monarch Money

[Monarch Money](https://www.monarchmoney.com/) is a modern personal finance platform. moneyflow provides full integration with Monarch's API, combining their excellent web/mobile interface with keyboard-driven power-user workflows.

**Supported operations:**
- Bulk transaction editing (merchant names, categories)
- Multi-select operations
- Advanced search and filtering
- Time-based navigation
- Duplicate detection
- Hide from reports

### Amazon Purchases

Analyze Amazon purchase history with the same interface. Import CSV files from your personal tracking or Amazon's order history exports.

**Features:**
- Import CSV with automatic deduplication
- Category normalization
- View by item, category, or time period
- Edit item names and categories
- Track quantity and price per item
- SQLite storage (no cloud dependencies)

**Getting started:**
```bash
# Import your CSV
moneyflow amazon import ~/Downloads/amazon-purchases.csv

# Launch the UI
moneyflow amazon

# Use custom database location
moneyflow amazon --db-path ~/my-amazon-data.db
```

**Expected CSV format:**
```csv
Order Date,Title,Category,Quantity,Item Total
01/15/2024,Python Crash Course,Books,1,39.99
01/20/2024,USB-C Cable,Electronics,2,15.99
```

### Demo Mode

Try the application without any account:

```bash
moneyflow --demo
```

- No authentication required
- Realistic synthetic data (~1000 transactions for dual-income household)
- Safe exploration (changes don't affect real accounts)
- All features enabled

Perfect for learning the interface or showcasing features.

### Other Platforms (Planned)

moneyflow uses a pluggable backend architecture. Planned platforms:
- 🚧 YNAB (You Need A Budget)
- 🚧 Lunch Money
- 🚧 Custom backends (contributions welcome)

## CLI Options

By default, moneyflow fetches all transactions. For faster startup, limit the data range:

**Current month only:**
```bash
moneyflow --mtd
```

**Recent years:**
```bash
moneyflow --year 2025
```

**From specific date:**
```bash
moneyflow --since 2024-06-01
```

**Enable caching:**
```bash
# Cache data to avoid re-downloading
moneyflow --cache

# Force refresh (skip cache)
moneyflow --refresh
```

**All options:**
```bash
moneyflow --help
```

## First Run Setup (Monarch Money)

On first run, moneyflow will guide you through credential setup:

1. **Get your 2FA secret** (before starting):
   - Log into Monarch Money → Settings → Security
   - Disable and re-enable 2FA
   - Click "Can't scan?" to view the secret key
   - Copy the BASE32 secret (e.g., `JBSWY3DPEHPK3PXP`)

2. **Launch moneyflow** and enter when prompted:
   - Monarch Money email and password
   - Your 2FA secret key
   - A new encryption password (for moneyflow only)

3. **Done!** Next time, just enter your encryption password.

Your credentials are encrypted with AES-128 and stored in `~/.moneyflow/credentials.enc`.

**To reset credentials**: Click "Reset Credentials" on the unlock screen.

## Time Navigation

moneyflow downloads all transactions once, then filters client-side for instant switching.

**Keyboard shortcuts:**
- `y` - Current year
- `t` - Current month
- `a` - All time
- `←` / `→` - Previous/next period

## Usage Examples

### Clean Up Merchant Names

```
1. Launch: moneyflow
2. Press 'g' to cycle to merchants view
3. Navigate to a merchant (e.g., "AMZN*ABC123")
4. Press 'm' to edit all transactions for that merchant
5. Type clean name (e.g., "Amazon") and press Enter
6. Press 'w' to review, then Enter to commit
```

### Bulk Edit Categories

```
1. Press 'u' to view all transactions
2. Press Space to select multiple transactions (shows ✓)
3. Press 'c' to edit category
4. Type to filter, press Enter to select
5. Press 'w' to review, then Enter to commit
```

### Monthly Spending Review

```
1. Press 't' for current month
2. Press 'g' to group by category
3. Press Enter on a category to see transactions
4. Review and edit as needed
5. Press '←' to view previous month
```

## Keyboard Shortcuts

### Views
- `g`: Cycle grouping (Merchant → Category → Group → Account)
- `u`: All transactions (ungrouped)
- `D`: Find duplicates

### Time
- `y`: Current year
- `t`: Current month
- `a`: All time
- `←` / `→`: Previous/next period

### Editing (detail view)
- `m`: Edit merchant
- `c`: Edit category
- `h`: Hide/unhide from reports
- `Space`: Multi-select
- `i`: View details

### Other
- `s`: Toggle sort (count/amount)
- `v`: Reverse sort order
- `f`: Filters (transfers, hidden items)
- `w`: Review and commit changes
- `q`: Quit
- `?`: Help

## Architecture

### Backend System
- Abstract base class defines required methods
- Monarch Backend: GraphQL API implementation
- Demo Backend: Synthetic data generator
- Extensible for YNAB, Lunch Money, or custom platforms

### Technology
- **Polars**: Fast data aggregation
- **Textual**: Terminal UI framework
- **Python 3.11+**: Required
- **Parquet**: Caching format (when --cache used)

### Performance
- Fetches all transactions on startup (1000 per batch)
- Local aggregations using Polars (instant filtering/grouping)
- Parallel API updates for speed

## Troubleshooting

### ModuleNotFoundError

**Solution**: Reinstall dependencies
```bash
pip install --upgrade moneyflow
# Or from source: uv sync
```

### "uv: command not found"

**Solution**: Restart terminal or add to PATH:
```bash
export PATH="$HOME/.cargo/bin:$PATH"
source ~/.bashrc  # or ~/.zshrc
```

### Login fails with "Incorrect password"

**Solutions**:
1. Enter the **encryption password** (moneyflow password), not Monarch password
2. If forgotten, click "Reset Credentials"
3. Manually delete: `rm -rf ~/.moneyflow/`

### 2FA/TOTP secret not working

**Solutions**:
1. Copy the **BASE32 secret** (long string like `JBSWY3DPEHPK3PXP`), not QR code
2. Remove any spaces from the secret
3. Get fresh secret by disabling/re-enabling 2FA

### Terminal displays weird characters

**Solution**: Use a modern terminal with Unicode and ANSI support:
- **macOS**: Terminal.app or [iTerm2](https://iterm2.com/)
- **Linux**: GNOME Terminal, Alacritty, or Kitty
- **Windows**: [Windows Terminal](https://apps.microsoft.com/store/detail/windows-terminal/9N0DX20HK701)

### Complete reset

```bash
# Delete all data
rm -rf ~/.moneyflow/
rm -rf .mm/

# Reinstall
pip install --upgrade --force-reinstall moneyflow

# Run again
moneyflow
```

## Getting Help

- **Bug Reports**: [GitHub Issues](https://github.com/wesm/moneyflow/issues)
- **Questions**: Check existing issues or open a new one

## Security

- Credentials encrypted with AES-128 using PBKDF2 (100,000 iterations)
- Encryption password never leaves your machine
- Stored in `~/.moneyflow/credentials.enc` with 600 permissions (owner-only)
- See [SECURITY.md](SECURITY.md) for details

## Contributing

Contributions welcome! This project uses:
- **uv** for dependency management: `uv sync`
- **pytest** for testing: `uv run pytest`
- **pyright** for type checking: `uv run pyright moneyflow/`
- **ruff** for linting/formatting: `uv run ruff check moneyflow/`

Development workflow:
```bash
# Clone and setup
git clone https://github.com/wesm/moneyflow.git
cd moneyflow
uv sync

# Run tests (must pass before committing)
uv run pytest

# Type check
uv run pyright moneyflow/

# Format and lint
uv run ruff format moneyflow/ tests/
uv run ruff check moneyflow/ tests/

# Run from source
uv run moneyflow --demo
```

## Acknowledgments

### Monarch Money Integration
This project's Monarch Money backend uses code derived from the [monarchmoney](https://github.com/hammem/monarchmoney) Python client library by hammem, used under the MIT License. See [licenses/monarchmoney-LICENSE](licenses/monarchmoney-LICENSE) for details.

Monarch Money® is a trademark of Monarch Money, Inc. This project is independent and not affiliated with, endorsed by, or officially connected to Monarch Money, Inc.

## License

MIT License - see [LICENSE](LICENSE) file for details
