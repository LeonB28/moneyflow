# Monarch Money Power User Interface

A keyboard-driven terminal interface for power users to efficiently manage Monarch Money transactions.

Currently implements a Terminal UI (TUI). Future versions may include web-based interfaces.

**Quick Start**:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh  # Install uv
git clone <repo-url> && cd monarch-pui             # Download
uv sync                                            # Install dependencies
uv run python -m monarch_tui                       # Run
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

## Installation

### 1. Install uv

Install uv (a Python package manager): https://docs.astral.sh/uv/getting-started/installation/

### 2. Download Monarch PUI

**Clone the repository:**
```bash
git clone https://github.com/yourusername/monarch-pui.git
cd monarch-pui
```

**Or download ZIP** from GitHub, extract, and navigate to the folder.

### 3. Install Dependencies

```bash
uv sync
```

This installs Python 3.11+ (if needed) and all dependencies automatically.

### 4. Run the TUI

```bash
uv run python -m monarch_tui
```

The first time you run it, you'll go through a one-time credential setup.

## CLI Options

By default, the application fetches **all transactions** from your account. For very large accounts, you can limit the data range:

**Fetch only recent years:**
```bash
# Only load transactions from 2025 onwards
uv run python -m monarch_tui --year 2025

# Only load transactions from 2024 onwards
uv run python -m monarch_tui --year 2024
```

**Fetch from a specific date:**
```bash
# Load transactions from June 1, 2024 onwards
uv run python -m monarch_tui --since 2024-06-01
```

**View all options:**
```bash
uv run python -m monarch_tui --help
```

**Note**: Limiting the date range makes initial load faster but you won't see older transactions in your analysis.

### First Run Setup

On first run, the TUI will walk you through credential setup:

1. **Get your 2FA secret** (before you start):
   - Log into Monarch Money on the web
   - Go to Settings → Security
   - Disable and re-enable 2FA
   - Click "Can't scan?" to view the secret key
   - Copy the BASE32 secret (e.g., `JBSWY3DPEHPK3PXP`)

2. **Launch TUI** and enter when prompted:
   - Monarch Money email and password
   - Your 2FA secret key
   - A new encryption password (for monarch-pui only)

3. **Done!** Next time you launch, just enter your encryption password.

Your credentials are encrypted with AES-128 and stored in `~/.monarch_tui/credentials.enc`.

**To reset credentials**: Click "Reset Credentials" on the unlock screen.

## Time Navigation

Monarch Money PUI downloads all transactions once, then filters client-side for fast switching between time periods.

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
1. Launch: uv run python -m monarch_tui
2. Press 'm' to view merchants
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
- `m`: Merchants
- `c`: Categories
- `g`: Groups
- `u`: All transactions (ungrouped)
- `D`: Find duplicates

### Time Navigation
- `y`: Current year
- `t`: Current month
- `a`: All time
- `1-9`: Specific months (1=Jan, 2=Feb, etc.)
- `←` / `→`: Previous/next period

### Editing (in detail view)
- `e`: Edit merchant name
- `r`: Recategorize
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

- **Polars**: Data aggregation and filtering
- **Textual**: Terminal UI framework
- **MonarchMoney API**: GraphQL client
- **Python 3.11+**: Required runtime

## Performance

- Fetches all transactions on startup (1000 per batch)
- Aggregations performed locally using Polars
- Updates committed in parallel to Monarch API

## Troubleshooting

### "ModuleNotFoundError" when running

**Problem**: You see errors like `ModuleNotFoundError: No module named 'textual'`

**Solution**: Run `uv sync` first to install all dependencies:
```bash
cd monarch-pui
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
1. Make sure you're entering the **encryption password** (the one you created for monarch-pui), not your Monarch Money password
2. If you forgot it, click "Reset Credentials" and go through setup again
3. If setup fails, you can manually delete: `rm -rf ~/.monarch_tui/`

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
4. Check for error messages in `~/.monarch_tui/logs` (if logging is enabled)

### I want to start over completely

To completely reset:
```bash
# Delete all stored data
rm -rf ~/.monarch_tui/

# Reinstall dependencies
cd monarch-pui
uv sync --reinstall

# Run again
uv run python -m monarch_tui
```

## Getting Help

- **Bug Reports**: [Open an issue on GitHub](https://github.com/yourusername/monarch-pui/issues)
- **Questions**: Check existing issues or open a new one
- **Development**: See [CLAUDE.md](CLAUDE.md) for development documentation

## Security

- Credentials are encrypted with AES-128 using PBKDF2 (100,000 iterations)
- Encryption password never leaves your machine
- Stored in `~/.monarch_tui/credentials.enc` with 600 permissions (owner-only)
- See [SECURITY.md](SECURITY.md) for full security documentation

## Contributing

Contributions welcome! See [CLAUDE.md](CLAUDE.md) for:
- Development setup
- Test-driven development workflow
- Code style guidelines
- How to run tests

## Acknowledgments

This project includes code from the [monarchmoney](https://github.com/hammem/monarchmoney) Python client library by hammem, used under the MIT License. See [licenses/monarchmoney-LICENSE](licenses/monarchmoney-LICENSE) for details.

## License

MIT License - see [LICENSE](LICENSE) file for details
