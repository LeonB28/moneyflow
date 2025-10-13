# moneyflow

**Track your moneyflow from the terminal.**

A blazing-fast, keyboard-driven TUI for managing personal finance transactions. Built for power users who want speed and efficiency.

**Currently Supported Platforms:**
- ✅ **Monarch Money** (full support)
- ✅ **Demo Mode** (synthetic data for testing)
- 🚧 Other platforms (YNAB, Lunch Money - planned)

**Disclaimer**: This is an independent open-source project and is **not affiliated with, endorsed by, or connected to Monarch Money, Inc.** Monarch Money is a trademark of Monarch Money, Inc.

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
# Run with your Monarch Money account
moneyflow

# Try demo mode (no account needed)
moneyflow --demo

# Load only recent data
moneyflow --year 2025
```

## Features

- **Keyboard-driven**: Vim-inspired keyboard shortcuts (hjkl, Enter to drill down, Esc to go back)
- **Aggregated views**: View spending by Merchant, Category, or Category Group
- **Bulk editing**: Multi-select transactions with Space and batch update merchant names or categories
- **Type-to-search**: Filter categories and merchants as you type
- **Offline-first**: Fetch all data once, edit locally, then commit changes to API
- **Time navigation**: Navigate between months and years with arrow keys
- **Review before commit**: See all pending changes before saving to Monarch Money
- **Encrypted credentials**: AES-128 encryption with PBKDF2 key derivation (100,000 iterations)

## Supported Platforms

### Monarch Money
Full support for [Monarch Money](https://www.monarchmoney.com/) personal finance platform.

Features:
- Bulk transaction editing (merchant names, categories)
- Multi-select operations
- Search and filtering
- Time-based analysis
- Duplicate detection

### Demo Mode
Try the application without any account:

```bash
moneyflow --demo
```

Demo mode provides:
- **No authentication required** - skips credential setup
- **Realistic synthetic data** - ~1000 transactions for a dual-income household
- **Safe exploration** - changes don't affect any real account
- **All features enabled** - edit, search, categorize, filter, etc.

Perfect for:
- Trying before signing up for a finance platform
- Learning the interface
- Showcasing features
- Development without affecting real data

## Development Setup

If you want to contribute or modify the code:

```bash
# Clone the repository
git clone https://github.com/wesm/moneyflow.git
cd moneyflow

# Install dependencies
uv sync

# Run from source
uv run moneyflow

# Run tests
uv run pytest
```

## CLI Options

By default, moneyflow fetches **all transactions** from your account. For very large accounts, you can limit the data range:

**Fetch only recent years:**
```bash
# Only load transactions from 2025 onwards
moneyflow --year 2025

# Only load transactions from 2024 onwards
moneyflow --year 2024
```

**Fetch from a specific date:**
```bash
# Load transactions from June 1, 2024 onwards
moneyflow --since 2024-06-01
```

**Enable caching for faster startup:**
```bash
# Cache data to avoid re-downloading
moneyflow --cache

# Force refresh (skip cache)
moneyflow --refresh
```

**View all options:**
```bash
moneyflow --help
```

**Note**: Limiting the date range makes initial load faster but you won't see older transactions in your analysis.

### First Run Setup (Monarch Money)

On first run with Monarch Money, the TUI will walk you through credential setup:

1. **Get your 2FA secret** (before you start):
   - Log into Monarch Money on the web
   - Go to Settings → Security
   - Disable and re-enable 2FA
   - Click "Can't scan?" to view the secret key
   - Copy the BASE32 secret (e.g., `JBSWY3DPEHPK3PXP`)

2. **Launch moneyflow** and enter when prompted:
   - Monarch Money email and password
   - Your 2FA secret key
   - A new encryption password (for moneyflow only)

3. **Done!** Next time you launch, just enter your encryption password.

Your credentials are encrypted with AES-128 and stored in `~/.moneyflow/credentials.enc`.

**To reset credentials**: Click "Reset Credentials" on the unlock screen.

## Time Navigation

moneyflow downloads all transactions once, then filters client-side for fast switching between time periods.

**Keyboard shortcuts:**
- `y` - View current year
- `t` - View current month
- `a` - View all time
- `1-9` - View specific months (1=Jan, 2=Feb, etc.)
- `←` / `→` - Navigate to previous/next period

**Workflow:**
```
1. Launch TUI (downloads all transactions, may take 1-2 minutes for large accounts)
2. Default view: Current year
3. Press 't' to switch to current month
4. Press '←' to view previous month
5. Press 'y' to return to year view
6. Press 'a' to view all time
```

Time period changes are applied instantly using client-side filtering.

## Usage Examples

### Example 1: Edit a Merchant Name

```
1. Launch: moneyflow
2. Press 'g' to cycle to merchants view
3. Navigate to a merchant with arrow keys
4. Press 'e' to edit all transactions for that merchant
5. Type the new name and press Enter
6. Press 'w' to review changes
7. Press 'c' to commit to Monarch Money
```

### Example 2: Bulk Recategorize Transactions

```
1. Press 'u' to view all transactions
2. Press Space to select multiple transactions (shows ✓)
3. Press 'r' to recategorize
4. Type to filter categories, press Enter to select
5. Press 'w' to review changes
6. Press 'c' to commit
```

### Example 3: Monthly Spending Review

```
1. Press 't' to view current month
2. Press 'c' to group by category
3. Press Enter on a category to see transactions
4. Review and edit as needed
5. Press '←' to view previous month
```

## Keyboard Shortcuts

### Views
- `g`: Cycle grouping (Merchant → Category → Group → Account)
- `u`: All transactions (ungrouped)
- `D`: Find duplicates
- `c`: Categories (direct)
- `A`: Accounts (direct)

### Time Navigation
- `y`: Current year
- `t`: Current month
- `a`: All time
- `1-9`: Specific months (1=Jan, 2=Feb, etc.)
- `←` / `→`: Previous/next period

### Editing (in detail view)
- `m`: Edit merchant name
- `r`: Recategorize
- `h`: Hide/unhide from reports
- `d`: Delete transaction
- `Space`: Multi-select
- `i`: View transaction details

### Sorting
- `s`: Toggle count/amount
- `v`: Reverse order

### Other
- `f`: Filters (transfers, hidden items)
- `w`: Review and commit changes
- `q`: Quit
- `?`: Help

## Architecture

### Pluggable Backend System
The application uses a backend abstraction layer, allowing support for multiple finance platforms:

- **Backend Interface**: Abstract base class defines required methods
- **Monarch Backend**: Implementation for Monarch Money GraphQL API
- **Demo Backend**: Synthetic data for testing
- **Future**: Easy to add YNAB, Lunch Money, or other platforms

### Technology Stack
- **Polars**: Fast data aggregation and filtering
- **Textual**: Terminal UI framework
- **Python 3.11+**: Required runtime
- **Parquet**: Optional caching format (when --cache used)

## Performance

- Fetches all transactions on startup (1000 per batch)
- Aggregations performed locally using Polars
- Updates committed in parallel to Monarch API

## Troubleshooting

### "ModuleNotFoundError" when running

**Problem**: You see errors like `ModuleNotFoundError: No module named 'textual'`

**Solution**: Reinstall moneyflow:
```bash
pip install --upgrade moneyflow
```

Or if running from source:
```bash
cd moneyflow
uv sync
```

### "uv: command not found"

**Problem**: After installing uv, the terminal says it can't find the command

**Solution**: Restart your terminal, or manually add uv to your PATH:
```bash
# macOS/Linux - add to ~/.bashrc or ~/.zshrc
export PATH="$HOME/.cargo/bin:$PATH"
source ~/.bashrc  # or ~/.zshrc
```

### Login fails with "Incorrect password"

**Problem**: The TUI says "Incorrect password" when trying to unlock credentials

**Solutions**:
1. Make sure you're entering the **encryption password** (the one you created for moneyflow), not your Monarch Money password
2. If you forgot it, click "Reset Credentials" and go through setup again
3. If setup fails, you can manually delete: `rm -rf ~/.moneyflow/`

### 2FA/TOTP secret not working

**Problem**: Login fails even with correct credentials

**Solutions**:
1. Make sure you copied the **BASE32 secret** (the long string like `JBSWY3DPEHPK3PXP`), not the QR code
2. Remove any spaces from the secret key
3. Get a fresh secret by disabling and re-enabling 2FA in Monarch Money settings

### Terminal displays weird characters or colors

**Problem**: The UI looks broken with strange characters

**Solution**: Use a modern terminal emulator that supports Unicode and ANSI colors:
- **macOS**: Terminal.app (built-in) or [iTerm2](https://iterm2.com/)
- **Linux**: GNOME Terminal, Alacritty, or Kitty
- **Windows**: [Windows Terminal](https://apps.microsoft.com/store/detail/windows-terminal/9N0DX20HK701)

### "Cannot import name 'PBKDF2HMAC'"

**Problem**: Error about cryptography imports

**Solution**: Your dependencies are out of date. Run:
```bash
uv sync --reinstall
```

### The TUI is blank or frozen after login

**Problem**: TUI launches but nothing shows up after entering credentials

**Solution**: This may be a data loading issue. Try:
1. Check your internet connection
2. Check the terminal size (make it larger)
3. Wait 30 seconds for data to load
4. Run with `--dev` flag to see error messages: `moneyflow --dev`

### I want to start over completely

To completely reset:
```bash
# Delete all stored data
rm -rf ~/.moneyflow/

# Delete session
rm -rf .mm/

# Reinstall (if installed from PyPI)
pip install --upgrade --force-reinstall moneyflow

# Run again
moneyflow
```

## Getting Help

- **Bug Reports**: [Open an issue on GitHub](https://github.com/wesm/moneyflow/issues)
- **Questions**: Check existing issues or open a new one
- **Development**: See [CLAUDE.md](CLAUDE.md) for development documentation

## Security

- Credentials are encrypted with AES-128 using PBKDF2 (100,000 iterations)
- Encryption password never leaves your machine
- Stored in `~/.moneyflow/credentials.enc` with 600 permissions (owner-only)
- See [SECURITY.md](SECURITY.md) for full security documentation

## Contributing

Contributions welcome! See [CLAUDE.md](CLAUDE.md) for:
- Development setup
- Test-driven development workflow
- Code style guidelines
- How to run tests

## Acknowledgments

### Monarch Money Integration
This project's Monarch Money backend uses code derived from the [monarchmoney](https://github.com/hammem/monarchmoney) Python client library by hammem, used under the MIT License. See [licenses/monarchmoney-LICENSE](licenses/monarchmoney-LICENSE) for details.

Monarch Money® is a trademark of Monarch Money, Inc. This project is an independent tool and is not affiliated with, endorsed by, or officially connected to Monarch Money, Inc.

## License

MIT License - see [LICENSE](LICENSE) file for details
