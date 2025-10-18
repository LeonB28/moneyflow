# Testing Amazon Mode - Manual Test Guide

This guide helps you test the Amazon purchase analysis feature in moneyflow.

## Prerequisites

- Python 3.11+
- uv package manager
- Your Amazon purchase CSV file

## Quick Start

### 1. Verify Installation

```bash
# Make sure dependencies are synced
uv sync

# Test that CLI works
uv run moneyflow --help

# Test Amazon commands
uv run moneyflow amazon --help
```

Expected output: Help text showing amazon subcommands (import, status, launch).

### 2. Import Your Amazon Data

```bash
# Import your CSV file
uv run moneyflow amazon import ~/path/to/your/amazon-purchases.csv
```

**Expected CSV Format:**
```
Order Date,Title,Category,Quantity,Item Total,Reimbursed,Year,Regret,Disposed,Sale Price
01/15/2024,Python Crash Course,Books,1,39.99,,,,,
01/20/2024,USB-C Cable,Electronics,2,15.99,,,,,
```

**Expected Output:**
```
Importing Amazon purchases from /path/to/file.csv...
Parsed 100 items from CSV
Created 15 new categories
Imported 100 new transactions

Database summary:
  Total transactions: 100
  Date range: 2024-01-15 to 2024-10-18
  Total spent: $2,547.89
  Unique items: 95
  Categories: 15

Launch moneyflow: $ moneyflow amazon
```

**What It Does:**
- Parses CSV with Polars
- Normalizes categories (BOoks → Books, VIdeo Game → Video Game)
- Converts amounts to negative (expenses)
- Calculates price per item
- Generates deterministic transaction IDs for deduplication
- Stores in ~/.moneyflow/amazon.db

### 3. Check Import Status

```bash
uv run moneyflow amazon status
```

**Expected Output:**
```
Amazon Purchase Database

Location: /Users/yourname/.moneyflow/amazon.db

Statistics:
  Total transactions: 100
  Date range: 2024-01-15 to 2024-10-18
  Total spent: $2,547.89
  Unique items: 95
  Categories: 15

Import History:
  2024-10-18 14:30:22: amazon-purchases.csv (100 imported, 0 duplicates)
```

### 4. Test Duplicate Detection

```bash
# Import the same file again
uv run moneyflow amazon import ~/path/to/your/amazon-purchases.csv
```

**Expected Output:**
```
Importing Amazon purchases from /path/to/file.csv...
Parsed 100 items from CSV
Skipped 100 duplicates
Imported 0 new transactions
```

**Test Force Reimport:**
```bash
uv run moneyflow amazon import --force ~/path/to/your/amazon-purchases.csv
```

Expected: Updates existing transactions, shows "Updated 100 existing transactions".

### 5. Launch Amazon Mode UI

```bash
uv run moneyflow amazon
```

**What To Test:**

#### Backend Functionality
- [  ] UI launches without errors
- [  ] Title shows "moneyflow [Amazon]"
- [  ] Transactions load correctly
- [  ] All your imported purchases are visible

#### Basic Navigation (Same as Monarch)
- [  ] `j/k` or arrow keys navigate transactions
- [  ] `Enter` drills down (currently not adapted for Amazon)
- [  ] `Esc` goes back
- [  ] `q` quits

#### Time Navigation
- [  ] `y` - This year view
- [  ] `t` - This month view
- [  ] `a` - All time view
- [  ] `←` - Previous period
- [  ] `→` - Next period

#### Grouping
- [  ] `g` - Cycles through grouping modes
- [  ] **Note**: Should cycle Item → Category (not Merchant → Category → Group → Account)
- [  ] **Known Issue**: Currently shows all Monarch modes

#### Editing
- [  ] `m` - Edit item name (merchant field)
- [  ] **Note**: Column should say "Item" not "Merchant"
- [  ] **Known Issue**: Currently says "Merchant"
- [  ] `c` - Edit category
- [  ] `h` - Toggle hide from reports
- [  ] `w` - Review and commit changes

#### Detail View
- [  ] `i` - Show transaction details
- [  ] **Should show**: Quantity, Price per Item
- [  ] **Known Issue**: May not show Amazon-specific fields yet

## Test Monarch Mode Still Works

**Critical:** Make sure we didn't break Monarch mode!

```bash
# Test demo mode (no credentials needed)
uv run moneyflow --demo
```

**What To Test:**
- [  ] Demo mode launches
- [  ] Transactions load
- [  ] All grouping modes work (Merchant, Category, Group, Account)
- [  ] Editing works
- [  ] Time navigation works
- [  ] No errors or crashes

**If you have Monarch credentials:**
```bash
# Test real Monarch mode
uv run moneyflow
```

Expected: Should work exactly as before, no changes to functionality.

## Known Limitations (To Be Fixed)

1. **Column Names**: Shows "Merchant" instead of "Item" in Amazon mode
2. **Grouping Modes**: Shows all 4 modes instead of just Item/Category
3. **Detail View**: May not show Quantity/Price per Item fields
4. **Accounts/Groups**: Amazon mode shouldn't show these options

## Debugging

### Check Database Directly

```bash
sqlite3 ~/.moneyflow/amazon.db

# See all tables
.tables

# Count transactions
SELECT COUNT(*) FROM transactions;

# See categories
SELECT * FROM categories;

# See import history
SELECT * FROM import_history;

# Exit
.quit
```

### Check Logs

Logs are written to `~/.moneyflow/logs/moneyflow.log`:

```bash
tail -f ~/.moneyflow/logs/moneyflow.log
```

### Delete and Start Over

```bash
# Remove Amazon database
rm ~/.moneyflow/amazon.db

# Re-import
uv run moneyflow amazon import ~/path/to/csv
```

## Test Results Template

Copy this and fill it out:

```markdown
## Test Results - Amazon Mode

**Date**: 2024-10-18
**Branch**: amazon-data
**Commit**: [commit hash]

### Import Tests
- [ ] Initial import: PASS/FAIL
- [ ] Duplicate detection: PASS/FAIL
- [ ] Force reimport: PASS/FAIL
- [ ] Status command: PASS/FAIL

### UI Launch
- [ ] Amazon mode launches: PASS/FAIL
- [ ] Transactions visible: PASS/FAIL
- [ ] No errors on startup: PASS/FAIL

### Navigation
- [ ] Basic navigation (j/k/Enter/Esc): PASS/FAIL
- [ ] Time navigation (y/t/a/arrows): PASS/FAIL
- [ ] Grouping toggle (g): PASS/FAIL

### Editing
- [ ] Edit item name: PASS/FAIL
- [ ] Edit category: PASS/FAIL
- [ ] Hide toggle: PASS/FAIL
- [ ] Commit changes: PASS/FAIL

### Monarch Compatibility
- [ ] Demo mode works: PASS/FAIL
- [ ] Monarch mode works: PASS/FAIL (if tested)

### Issues Found
1. [List any issues, crashes, or unexpected behavior]
2. 
3. 

### Notes
[Any additional observations]
```

## Next Steps After Testing

1. Report test results
2. Identify any crashes or critical bugs
3. Prioritize UI fixes (column names, grouping modes)
4. Test with larger datasets
5. Test edge cases (empty database, corrupted CSV, etc.)

## Questions?

If you encounter issues:
1. Check logs in `~/.moneyflow/logs/moneyflow.log`
2. Try with `--demo` mode to isolate Amazon-specific issues
3. Verify database exists: `ls -lh ~/.moneyflow/amazon.db`
4. Check import history: `moneyflow amazon status`
