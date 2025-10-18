# Amazon Purchase Analysis Mode

moneyflow includes a dedicated mode for analyzing Amazon purchase history. This allows you to import, categorize, and explore your Amazon purchases using the same powerful terminal UI.

## Overview

Amazon mode provides:

- Import Amazon purchase data from CSV files
- Automatic deduplication across imports
- Category normalization and management
- SQLite storage (local, no cloud dependencies)
- Same TUI experience as Monarch mode
- Track quantity and price per item

## Getting Started

### 1. Import Your Purchase Data

```bash
# Import from CSV file
moneyflow amazon import ~/Downloads/amazon-purchases.csv
```

The import will:
- Parse the CSV and validate data
- Normalize category names (e.g., "BOoks" → "Books")
- Detect and skip duplicates
- Calculate price per item
- Store everything in SQLite

### 2. Check Import Status

```bash
# View database statistics
moneyflow amazon status
```

This shows:
- Total transactions imported
- Date range of purchases
- Total amount spent
- Number of unique items and categories
- Import history

### 3. Launch the UI

```bash
# Open the terminal UI
moneyflow amazon
```

Uses the same keyboard-driven interface as Monarch mode.

## CSV Format

### Personal Format (Currently Supported)

Your personal Amazon purchase tracking CSV:

```csv
Order Date,Title,Category,Quantity,Item Total,Reimbursed,Year,Regret,Disposed,Sale Price
01/15/2024,Python Crash Course,Books,1,39.99,,,,,
01/20/2024,USB-C Cable,Electronics,2,15.99,,,,,
03/01/2024,Coffee Maker,Kitchen,1,89.99,,,,,
```

**Required columns:**
- `Order Date` - Purchase date (MM/DD/YYYY format)
- `Title` - Item name/description
- `Category` - Product category
- `Quantity` - Number of items (must be > 0)
- `Item Total` - Total cost (positive number)

Additional columns are ignored.

### Official Amazon Export (Planned)

Support for the official Amazon.com order history export format is planned for a future release. This will include automatic category mapping from Amazon's internal categories to moneyflow categories.

## Features

### Automatic Deduplication

Transactions are deduplicated based on a fingerprint of:
- Order date
- Item title
- Amount
- Quantity

This means you can safely re-import the same CSV file multiple times - duplicates will be automatically skipped.

```bash
# First import
moneyflow amazon import purchases.csv
# Output: Imported 100 new transactions

# Re-import (safe!)
moneyflow amazon import purchases.csv
# Output: Skipped 100 duplicates, Imported 0 new transactions
```

### Category Normalization

Common category variants are automatically normalized:
- `BOoks` → `Books`
- `VIdeo Game` → `Video Game`
- `Office Products` → `Office Product`

This ensures consistent categorization even if your CSV has typos or variants.

### Incremental Imports

Amazon mode supports incremental imports, preserving any manual edits you've made:

1. Import initial data
2. Edit categories and item names in the UI
3. Import updated CSV with new purchases
4. Only new items are added - your edits are preserved

### Custom Database Location

By default, data is stored in `~/.moneyflow/amazon.db`. You can use a custom location:

```bash
# Use custom database
moneyflow amazon --db-path ~/Documents/amazon-purchases.db

# All commands support --db-path
moneyflow amazon --db-path ~/custom.db import purchases.csv
moneyflow amazon --db-path ~/custom.db status
```

## UI Navigation

Amazon mode uses the same keyboard shortcuts as Monarch mode:

### View Modes
- `g` - Cycle between Item and Category views
- `u` - View all transactions (ungrouped)

### Time Navigation
- `y` - Current year
- `t` - Current month
- `a` - All time
- `←/→` - Previous/next period

### Editing
- `m` - Edit item name
- `c` - Edit category
- `h` - Hide/unhide from reports
- `Space` - Multi-select for bulk operations
- `w` - Review and commit changes

### Other
- `?` - Show help
- `q` - Quit

See [Keyboard Shortcuts](keyboard-shortcuts.md) for the complete list.

## Data Model

### Transactions

Each Amazon purchase is stored as a transaction with:

- **ID**: Generated from fingerprint (for deduplication)
- **Date**: Purchase date
- **Item**: Item title/name (displayed as "Merchant" in UI)
- **Category**: Product category (editable)
- **Amount**: Total cost (negative, like expenses)
- **Quantity**: Number of items purchased
- **Price per Item**: Calculated unit price
- **Notes**: Additional info (e.g., "Qty: 2")
- **Hide from Reports**: Toggle visibility

### Categories

Categories are created automatically from your CSV. You can:
- Edit category assignments in the UI
- Rename categories
- Create new categories
- View spending by category

## Database

Amazon data is stored in a local SQLite database (default: `~/.moneyflow/amazon.db`).

**Tables:**
- `transactions` - Purchase records
- `categories` - Category definitions
- `import_history` - Audit trail of imports

**To inspect directly:**
```bash
sqlite3 ~/.moneyflow/amazon.db
.tables
SELECT * FROM import_history;
.quit
```

**To start fresh:**
```bash
# Delete database
rm ~/.moneyflow/amazon.db

# Re-import
moneyflow amazon import purchases.csv
```

## Limitations

- **Read-only**: No sync back to Amazon (local edits only)
- **No API**: Works with CSV files only (no live Amazon connection)
- **UI labels**: Currently shows Monarch-style labels (will be customized in future)

## Future Enhancements

Planned improvements:
- Support for official Amazon.com CSV export format
- Automatic category mapping from Amazon categories
- Seller name extraction
- Order-level grouping (multiple items per order)
- Returns and refunds tracking
- Subscription detection

## Troubleshooting

### Import fails with "Missing required columns"

**Cause**: CSV doesn't have the expected column names.

**Solution**: Verify your CSV has these exact column headers:
- `Order Date`
- `Title`
- `Category`
- `Quantity`
- `Item Total`

### "Amazon database is empty" when launching

**Cause**: No data has been imported yet.

**Solution**: Import your CSV first:
```bash
moneyflow amazon import ~/path/to/purchases.csv
```

### Duplicate transactions after import

**Cause**: Transaction fingerprints are different (different date/amount/quantity).

**Solution**: This is expected if the transactions are actually different. If they're true duplicates, check that the CSV columns match exactly.

## Tips

- **Start with a subset**: Test with a small CSV first (10-20 rows)
- **Check status often**: Use `moneyflow amazon status` to verify imports
- **Safe to experiment**: Edits are local only, delete the database to reset
- **Use custom paths**: Keep different analyses separate with `--db-path`

## Questions?

See the main [documentation](../index.md) or [open an issue](https://github.com/wesm/moneyflow/issues).
