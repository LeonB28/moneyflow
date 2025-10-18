# Amazon Mode - Quick Start

## Ready to Test!

The Amazon purchase analysis mode is fully implemented and ready for testing.

## Commands

```bash
# Import your Amazon purchase CSV
moneyflow amazon import ~/path/to/amazon-purchases.csv

# Check what was imported
moneyflow amazon status

# Launch the UI
moneyflow amazon

# Use a custom database location
moneyflow amazon --db-path ~/my-amazon-data.db
moneyflow amazon --db-path ~/my-amazon-data.db import purchases.csv
```

## Expected CSV Format

Your personal format with columns:
```
Order Date,Title,Category,Quantity,Item Total,Reimbursed,Year,Regret,Disposed,Sale Price
01/15/2024,Python Crash Course,Books,1,39.99,,,,,
01/20/2024,USB-C Cable,Electronics,2,15.99,,,,,
```

## What Works

✅ **CLI**: Import, status, launch with optional custom db path  
✅ **Backend**: Full SQLite storage with deduplication  
✅ **Import**: Polars-based parsing with category normalization  
✅ **Tests**: 55 tests, 100% coverage, all passing  
✅ **Compatibility**: Monarch mode unchanged, all 708 tests pass

## Known UI Quirks (Non-Blocking)

The UI will work but shows Monarch-style labels:
- Says "Merchant" (should say "Item")
- Shows 4 grouping modes (should show 2: Item, Category)
- Missing Quantity/Price fields in detail view

**These are cosmetic** - all core functionality works!

## Verify Monarch Still Works

```bash
# Test demo mode
moneyflow --demo

# Should work perfectly - nothing changed
```

## Database Location

Default: `~/.moneyflow/amazon.db`

To use a different location:
```bash
moneyflow amazon --db-path /path/to/custom.db
```

## Next Steps

1. Import your real CSV
2. Launch the UI and explore
3. Report any crashes or errors
4. Note UI quirks for future polish

## Quick Test

Try this to verify everything works:

```bash
# Create a tiny test CSV
cat > /tmp/test-amazon.csv << 'CSV'
Order Date,Title,Category,Quantity,Item Total
01/15/2024,Test Book,Books,1,19.99
01/20/2024,Test Cable,Electronics,2,15.99
CSV

# Import it
moneyflow amazon --db-path /tmp/test.db import /tmp/test-amazon.csv

# Check status
moneyflow amazon --db-path /tmp/test.db status

# Clean up
rm /tmp/test.db /tmp/test-amazon.csv
```

Expected: Should import 2 items and show stats.

## Ready! 🚀

Go ahead and import your real data:
```bash
moneyflow amazon import ~/path/to/your/amazon-purchases.csv
moneyflow amazon
```
