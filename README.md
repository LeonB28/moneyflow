# Monarch CLI

A blazing-fast terminal UI for power users to manage Monarch Money transactions.

## Features

- **Lightning-fast navigation**: Vim-inspired keyboard shortcuts
- **Aggregated views**: View transactions by Merchant, Category, or Group
- **Bulk editing**: Multi-select and batch update transactions
- **Fuzzy search**: Quickly find and filter transactions
- **Offline-first**: Fetch once, edit locally, batch commit
- **Time-based filtering**: Switch between months, years, or all-time views
- **Undo/Redo**: Track changes before committing

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the TUI (will prompt for login on first run)
python monarch_tui.py
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
- All aggregations done locally with Polars
- Batch updates committed in parallel
- Sub-100ms response time for all UI interactions
