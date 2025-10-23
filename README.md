# moneyflow

**Track your moneyflow from the terminal.**

A keyboard-driven terminal UI for managing personal finance transactions. Built for users who prefer efficiency and direct control over their financial data.

![moneyflow main screen](https://raw.githubusercontent.com/wesm/moneyflow-assets/main/home-screen.png)

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
moneyflow amazon import ~/Downloads/"Your Orders"
moneyflow amazon

# Load only recent data for faster startup (Monarch only)
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

Analyze Amazon purchase history using the official "Your Orders" data export from Amazon. Import and explore with the same powerful interface.

**Features:**
- Import from official Amazon data export (Your Orders.zip)
- Automatic deduplication and category assignment
- View by item, category, or time period
- Edit item names and categories
- Track quantity, pricing, and order status
- SQLite storage (no cloud dependencies)

**Getting started:**
```bash
# 1. Request your data from Amazon Account Settings > Privacy
#    (See docs/guide/amazon-mode.md for detailed instructions)

# 2. Unzip the "Your Orders.zip" file

# 3. Import the directory
moneyflow amazon import ~/Downloads/"Your Orders"

# 4. Launch the UI
moneyflow amazon
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

On first run, moneyflow will guide you through credential setup.

### Step 1: Select Backend

![Backend selection](https://raw.githubusercontent.com/wesm/moneyflow-assets/main/backend-select.png)

Choose which platform you want to connect to (currently only Monarch Money is fully supported).

### Step 2: Enter Credentials

![Credential setup](https://raw.githubusercontent.com/wesm/moneyflow-assets/main/monarch-credentials.png)

**Before starting, get your 2FA secret:**
1. Log into Monarch Money → Settings → Security
2. Disable and re-enable 2FA
3. Click "Can't scan?" to view the secret key
4. Copy the BASE32 secret (e.g., `JBSWY3DPEHPK3PXP`)

**Then enter in moneyflow:**
- Monarch Money email and password
- Your 2FA secret key
- A new encryption password (for moneyflow only)

**Done!** Next time, just enter your encryption password.

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

![Edit merchant from aggregate view](https://raw.githubusercontent.com/wesm/moneyflow-assets/main/drill-down-bulk-edit-merchant.png)

```
1. Launch: moneyflow
2. Press 'g' to cycle to merchants view
3. Navigate to a merchant (e.g., "AMZN*ABC123")
4. Press 'm' to edit all transactions for that merchant
5. Type clean name (e.g., "Amazon") and press Enter
6. Press 'w' to review, then Enter to commit
```

### Bulk Edit Categories

![Edit category with multi-select](https://raw.githubusercontent.com/wesm/moneyflow-assets/main/drill-down-edit-category.png)

```
1. Press 'u' to view all transactions
2. Press Space to select multiple transactions (shows ✓)
3. Press 'c' to edit category
4. Type to filter, press Enter to select
5. Press 'w' to review, then Enter to commit
```

### Drill Down and Sub-Grouping

![Drill into merchant and group by category](https://raw.githubusercontent.com/wesm/moneyflow-assets/main/drill-down-group-by-category.png)

Drill into any merchant or category, then press 'g' to cycle through sub-groupings:

```
1. From merchants view, press Enter on "Amazon"
2. Press 'g' to group by category (shows Amazon transactions by category)
3. Press 'g' again to group by account
4. Press 'g' again to show detail view
5. Press Esc to go back to merchants view
```

![Transaction detail view](https://raw.githubusercontent.com/wesm/moneyflow-assets/main/drill-down-detail.png)

### Multi-Select for Bulk Operations

![Multi-select transactions](https://raw.githubusercontent.com/wesm/moneyflow-assets/main/drill-down-detail-multi-select.png)

```
1. Navigate to any detail view
2. Press Space to select transactions (shows ✓)
3. Press 'm' or 'c' to bulk edit selected transactions
4. Press 'w' to review and commit
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

## Troubleshooting

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

## Acknowledgments

### Monarch Money Integration
This project's Monarch Money backend uses code derived from the [monarchmoney](https://github.com/hammem/monarchmoney) Python client library by hammem, used under the MIT License. See [licenses/monarchmoney-LICENSE](licenses/monarchmoney-LICENSE) for details.

Monarch Money® is a trademark of Monarch Money, Inc. This project is independent and not affiliated with, endorsed by, or officially connected to Monarch Money, Inc.

## License

MIT License - see [LICENSE](LICENSE) file for details
