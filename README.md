# Monarch TUI

A blazing-fast terminal UI for power users to manage Monarch Money transactions.

**Quick Start**:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh  # Install uv
git clone <repo-url> && cd monarch-tui             # Download
uv sync                                            # Install dependencies
uv run python -m monarch_tui                       # Run!
```

## Features

- **Lightning-fast navigation**: Vim-inspired keyboard shortcuts (`hjkl`, Enter to drill down, Esc to go back)
- **Aggregated views**: View spending by Merchant, Category, or Category Group with counts and totals
- **Bulk editing**: Multi-select transactions (Space) and batch update merchant names or categories
- **Fuzzy search**: Quickly find and filter transactions with `/` search
- **Offline-first**: Fetch all data once, edit locally with instant feedback, then batch commit to cloud
- **Time-based filtering**: Quick jump to months (1-9), this year (y), or all time (a)
- **Undo/Redo**: Full change tracking with undo (u) before committing - never lose work
- **Secure credentials**: AES-128 encrypted credential storage with PBKDF2 key derivation

## Installation

### 1. Install uv

`uv` is a fast Python package manager that handles everything (including Python itself).

**macOS and Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

After installation, **restart your terminal** or run:
```bash
source ~/.bashrc  # or ~/.zshrc on macOS
```

### 2. Download Monarch TUI

**Clone the repository:**
```bash
git clone https://github.com/yourusername/monarch-tui.git
cd monarch-tui
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

By default, Monarch TUI fetches **all transactions** from your account. For very large accounts, you can limit the data range:

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
   - A new encryption password (for monarch-tui only)

3. **Done!** Next time you launch, just enter your encryption password.

Your credentials are encrypted with AES-128 and stored in `~/.monarch_tui/credentials.enc`.

**To reset credentials**: Click "Reset Credentials" on the unlock screen.

## Usage Examples

### Example 1: View and Edit a Merchant Name

```
1. Launch the TUI: uv run python -m monarch_tui
2. Press 'm' to view merchants
3. Use arrow keys (or j/k) to navigate to a merchant
4. Press Enter to drill down and see all transactions for that merchant
5. Press 'e' to edit the merchant name
6. Type the new name and press Enter
7. Press Ctrl+S to save changes to Monarch Money
```

### Example 2: Bulk Categorize Transactions

```
1. Press 'm' to view merchants
2. Press Enter on a merchant to see transactions
3. Press Space to select multiple transactions
4. Press 'r' (recategorize) to change category
5. Select the new category
6. Press Ctrl+S to save all changes at once
```

### Example 3: Find and Hide Duplicate Transactions

```
1. Press '/' to search
2. Type "duplicate" or search for a specific merchant
3. Navigate to suspicious transactions
4. Press 'H' (capital H) to hide from reports
5. Press Ctrl+S to save
```

### Example 4: Quick Monthly Review

```
1. Press '1' for January (or '2' for Feb, '3' for Mar, etc.)
2. Press 'c' to view by category
3. Use h/l (or arrows) to toggle between sort by count and sort by amount
4. Press Enter on a category to drill down
5. Review transactions and make edits as needed
```

## Keyboard Shortcuts

### Navigation
- `m` / `c` / `g`: Switch to Merchant/Category/Group view
- `j` / `k` or `↓` / `↑`: Navigate rows
- `h` / `l` or `←` / `→`: Toggle sort (amount ↔ date)
- `Enter`: Drill down / Edit selected
- `Esc`: Go back / Cancel

### Time Frames
- `1-9`: Quick select months (1=Jan, 2=Feb, etc.)
- `y`: This year
- `a`: All time
- `<` / `>`: Previous/Next period

### Actions
- `Space`: Multi-select for bulk edit
- `e`: Edit merchant name
- `c`: Change category
- `h`: Toggle hide from reports
- `/`: Fuzzy search/filter
- `u`: Undo last change
- `Ctrl+S`: Save pending changes

### Commands (`:` vim-style)
- `:save` or `:w`: Save pending changes
- `:quit` or `:q`: Quit
- `:wq`: Save and quit
- `:refresh`: Re-fetch from API

## Architecture

- **Polars**: High-performance data aggregation and filtering
- **Textual**: Modern terminal UI framework
- **MonarchMoney API**: GraphQL client for Monarch Money
- **SQLite**: Decision persistence and change tracking

## Performance

- Bulk fetch all transactions on startup (1000 per batch)
- All aggregations done locally
- Batch updates committed in parallel

## Troubleshooting

### "ModuleNotFoundError" when running

**Problem**: You see errors like `ModuleNotFoundError: No module named 'textual'`

**Solution**: Run `uv sync` first to install all dependencies:
```bash
cd monarch-tui
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
1. Make sure you're entering the **encryption password** (the one you created for monarch-tui), not your Monarch Money password
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
cd monarch-tui
uv sync --reinstall

# Run again
uv run python -m monarch_tui
```

## Getting Help

- **Bug Reports**: [Open an issue on GitHub](https://github.com/yourusername/monarch-tui/issues)
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

## License

MIT License - see [LICENSE](LICENSE) file for details
