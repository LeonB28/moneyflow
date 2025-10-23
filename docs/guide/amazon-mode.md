# Amazon Purchase Analysis Mode

moneyflow includes a dedicated mode for analyzing Amazon purchase history using Amazon's official "Your Orders" data export. This allows you to import, categorize, and explore your Amazon purchases using the same powerful terminal UI.

## Overview

Amazon mode provides:

- Import from official Amazon "Your Orders" data export
- Automatic deduplication and category assignment
- SQLite storage (local, no cloud dependencies)
- Same TUI experience as Monarch mode
- Track quantity, pricing, and order status

## Getting Started

### 1. Request Your Amazon Data

**IMPORTANT**: You need to request your purchase history from Amazon first.

!!! note "How to Request Your Amazon Data"
    1. Log into your Amazon account
    2. Go to **Account Settings** → **Privacy** → **Request My Data**
    3. Select **"Your Orders"** (you don't need all your data)
    4. Submit the request
    5. Wait 1-3 days for Amazon to prepare your data
    6. Download the **Your Orders.zip** file when ready
    7. Unzip it to get the "Your Orders" directory

The directory will contain files like:
- `Retail.OrderHistory.1/Retail.OrderHistory.1.csv`
- `Retail.OrderHistory.2/Retail.OrderHistory.2.csv`
- etc.

### 2. Import Your Purchase Data

```bash
# Import from the unzipped directory
moneyflow amazon import ~/Downloads/"Your Orders"
```

The import will:
- Scan for all Retail.OrderHistory CSV files
- Parse and validate order data
- Assign categories automatically using Monarch category mappings
- Detect and skip duplicates
- Skip cancelled orders
- Store everything in SQLite

### 3. Check Import Status

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

### 4. Launch the UI

```bash
# Open the terminal UI
moneyflow amazon
```

Uses the same keyboard-driven interface as Monarch mode.

## CSV Format

moneyflow imports from the official Amazon "Your Orders" data export format.

### Expected Files

Files named: `Retail.OrderHistory.*.csv`

### Expected Columns

- **ASIN**: Amazon Standard Identification Number
- **Order ID**: Amazon order identifier
- **Order Date**: ISO timestamp (e.g., "2025-10-13T22:08:07Z")
- **Product Name**: Item description/title
- **Quantity**: Number of items ordered
- **Total Owed**: Final amount paid (after tax)
- **Unit Price**: Item price before tax
- **Order Status**: "Closed", "New", "Cancelled", etc.
- **Shipment Status**: "Shipped", "Delivered", etc.

### Category Assignment

Categories are automatically assigned using moneyflow's centralized category mappings (same as Monarch mode). You can edit categories in the UI after import.

## Features

### Automatic Deduplication

Transactions are deduplicated based on a unique ID generated from:
- ASIN (or product name hash if ASIN missing)
- Order ID

This means you can safely re-import the same directory multiple times - duplicates will be automatically skipped.

```bash
# First import
moneyflow amazon import ~/Downloads/"Your Orders"
# Output: Imported 100 new transactions

# Re-import (safe!)
moneyflow amazon import ~/Downloads/"Your Orders"
# Output: Skipped 100 duplicates, Imported 0 new transactions
```

Cancelled orders are automatically skipped during import.

### Incremental Imports

Amazon mode supports incremental imports, preserving any manual edits you've made:

1. Import initial data export
2. Edit categories and item names in the UI
3. Request and import a fresh data export from Amazon (with new purchases)
4. Only new orders are added - your edits are preserved
5. Use `--force` flag to re-import and overwrite existing transactions if needed

### Custom Database Location

By default, data is stored in `~/.moneyflow/amazon.db`. You can use a custom location:

```bash
# Use custom database
moneyflow amazon --db-path ~/Documents/amazon-purchases.db

# All commands support --db-path
moneyflow amazon --db-path ~/custom.db import ~/Downloads/"Your Orders"
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

- **ID**: Generated from ASIN + Order ID (for deduplication)
- **Date**: Order date
- **Merchant**: Product name (displayed as "Merchant" in UI)
- **Category**: Automatically assigned from category mappings (editable)
- **Amount**: Total Owed (negative, like expenses)
- **Quantity**: Number of items ordered
- **ASIN**: Amazon product identifier
- **Order ID**: Amazon order number
- **Order Status**: Order state (Closed, New, etc.)
- **Shipment Status**: Shipping state (Shipped, Delivered, etc.)
- **Notes**: Additional info (e.g., order details)
- **Hide from Reports**: Toggle visibility

### Categories

Categories are assigned automatically using moneyflow's centralized category module (shared with Monarch mode). You can:
- Edit category assignments in the UI
- View spending by category
- Categories are NOT stored in the database - they come from `categories.py`

## Database

Amazon data is stored in a local SQLite database (default: `~/.moneyflow/amazon.db`).

**Tables:**
- `transactions` - Order records (one row per item)
- `import_history` - Audit trail of imports

**To inspect directly:**
```bash
sqlite3 ~/.moneyflow/amazon.db
.tables
SELECT * FROM import_history;
SELECT COUNT(*) FROM transactions WHERE order_status = 'Closed';
.quit
```

**To start fresh:**
```bash
# Delete database
rm ~/.moneyflow/amazon.db

# Re-import
moneyflow amazon import ~/Downloads/"Your Orders"
```

## Limitations

- **Read-only**: No sync back to Amazon (local edits only)
- **Manual data export**: Requires requesting "Your Orders" export from Amazon
- **No live updates**: Must re-request data from Amazon to get new orders
- **Item-level only**: Each item in an order is a separate transaction (no order grouping)

## Future Enhancements

Planned improvements:
- Order-level grouping (link items from same order)
- Seller name extraction and filtering
- Returns and refunds tracking
- Subscription detection
- Amazon category to moneyflow category mapping improvements
- Custom category rules

## Troubleshooting

### Import fails with "No Retail.OrderHistory CSV files found"

**Cause**: The directory doesn't contain Amazon export files.

**Solution**:
1. Make sure you've unzipped the "Your Orders.zip" file
2. Point to the unzipped directory (not individual CSV files)
3. The directory should contain folders like `Retail.OrderHistory.1/`

### "Amazon database is empty" when launching

**Cause**: No data has been imported yet.

**Solution**: Import your data first:
```bash
moneyflow amazon import ~/Downloads/"Your Orders"
```

### Import shows "0 new transactions"

**Cause**: All transactions already exist in the database.

**Solution**:
- This is expected if you're re-importing the same data
- Use `--force` flag to re-import: `moneyflow amazon import --force ~/Downloads/"Your Orders"`
- Or delete the database and start fresh: `rm ~/.moneyflow/amazon.db`

### Missing ASIN for some items

**Cause**: Some Amazon items don't have ASINs (e.g., digital content, gift cards).

**Solution**: moneyflow automatically generates a pseudo-ASIN from the product name hash. This is normal and doesn't affect functionality.

## Tips

- **Check status often**: Use `moneyflow amazon status` to verify imports
- **Safe to experiment**: Edits are local only, delete the database to reset
- **Use custom paths**: Keep different analyses separate with `--db-path`
- **Re-import periodically**: Request fresh exports from Amazon to get new orders
- **Filter by status**: Use order status and shipment status to find specific orders

## Questions?

See the main [documentation](../index.md) or [open an issue](https://github.com/wesm/moneyflow/issues).
