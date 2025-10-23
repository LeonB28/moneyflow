# Navigation & Search

moneyflow provides multiple views of your transaction data and powerful search capabilities to find what you need quickly.

## View Types

Press `g` to cycle through aggregate views, or press `u` to view all transactions.

### Aggregate Views

Aggregate views group transactions by a specific field and show counts and totals.

**Cycle Order** (press `g` repeatedly):
Merchant → Category → Group → Account → Merchant...

**Merchant View**

- Shows spending grouped by merchant
- Columns: Merchant name, Transaction count, Total amount
- Sort by count, amount, or merchant name
- Press `Enter` to drill down to individual transactions

**Category View**

- Shows spending grouped by category
- See which categories consume your budget
- Quick way to spot overspending
- Press `Enter` to view transactions in that category

**Group View**

- High-level view of category groups
- Examples: Food & Dining, Travel, Housing, Income
- Best for monthly budget reviews
- Press `Enter` to see transactions in that group

**Account View**

- Spending per bank account or credit card
- Useful for reconciliation
- Track per-account cash flow
- Press `Enter` to view transactions for that account

**Amazon Mode Note**: In Amazon mode, the views have different names to reflect Amazon purchase data:
- Merchant → **Item** (product names)
- Category → **Category** (product categories)
- Group → **Order ID** (group by order)
- Account view is not available in Amazon mode

### Detail View

Press `u` to view all transactions (ungrouped), or press `Enter` from any aggregate view to see transactions for that item.

Shows individual transactions with all fields:

- Date, Merchant, Category, Account, Amount
- Visual indicators:
  - Checkmark (selected for bulk operations)
  - H (hidden from reports)
  - * (pending edit)
- Full editing capabilities

## Navigation Patterns

### Drill-Down

Navigate from aggregated views to detailed transactions:

```
Merchant View
    ↓ (Enter on "Amazon")
Detail View (filtered to Amazon transactions)
    ↓ (Escape)
Merchant View (cursor restored to "Amazon")
```

Press `Escape` to go back to the previous view. Your cursor position and scroll state are preserved.

### Sub-Grouping

When drilled down, press `g` to cycle through sub-groupings of the filtered data. For example:

```
Category View → Enter on "Groceries"
    ↓
Detail View (Groceries transactions)
    ↓ (Press 'g')
Merchant View (grouped by merchant, filtered to Groceries)
    ↓ (Press 'g')
Group View (grouped by category group, filtered to Groceries)
    ↓ (Press 'g')
Account View (grouped by account, filtered to Groceries)
    ↓ (Press 'g')
Detail View (back to ungrouped Groceries transactions)
```

This lets you answer questions like "Which merchants did I spend the most on for groceries?"

## Sorting

Press `s` to cycle through sort options. Available sort fields depend on the current view:

**Aggregate Views**:
- Field name (e.g., Merchant, Category, Item)
- Count (number of transactions)
- Amount (total spending)

**Detail Views**:
- Date
- Merchant
- Category
- Account
- Amount

Press `v` to reverse sort direction (ascending/descending).

## Time Navigation

Filter transactions by time period using keyboard shortcuts.

### Quick Time Filters

| Key | Time Period |
|-----|-------------|
| `t` | This month |
| `y` | This year |
| `a` | All time |

### Navigate Between Periods

| Key | Action |
|-----|--------|
| `←` (Left arrow) | Previous period |
| `→` (Right arrow) | Next period |

When you press left/right arrows, moneyflow moves to the previous or next period based on your current time filter:

- If viewing "This Month", arrows navigate to previous/next month
- If viewing "This Year", arrows navigate to previous/next year
- If viewing "All Time", arrows do nothing (no period to navigate)

The breadcrumb shows your current time filter (e.g., "March 2025", "2025", "All Time").

### Command-Line Time Filters

You can also filter time when launching moneyflow:

```bash
# Load only 2025 transactions
moneyflow --year 2025

# Load last 90 days
moneyflow --days 90

# Load specific month
moneyflow --month 2025-03
```

This is useful for faster startup with large transaction histories.

## Search

Press `/` to search transactions.

### How Search Works

The search modal allows you to filter transactions by text matching:

- Searches across: Merchant name, Category, Notes
- Case-insensitive
- Partial matching (e.g., "starbucks" matches "Starbucks Coffee")
- Results update as you type

### Using Search

1. Press `/` to open the search input
2. Type your search query
3. Press `Enter` to apply the search
4. Press `Escape` to clear search and return to the previous view

### Search Behavior

- Search filters persist across view changes
- Breadcrumb shows "Search: your query" when active
- Clear search by pressing `/` then `Enter` with empty input
- Or press `Escape` while search is active (if search was the last action)

## Multi-Select

Select multiple transactions or groups for bulk operations:

- Press `Space` to select the current row
- Press `Ctrl+A` to select all visible items
- Selected items show a checkmark indicator
- Perform bulk edits (merchant rename, category change, hide/unhide)

## Quick Reference

| Key | Action |
|-----|--------|
| `g` | Cycle through views (Merchant/Category/Group/Account) |
| `u` | All transactions (ungrouped) |
| `Enter` | Drill down to details |
| `Escape` | Go back to previous view |
| `s` | Cycle sort field |
| `v` | Reverse sort direction |
| `/` | Search |
| `f` | Filters (transfers, hidden) |
| `Space` | Select current row |
| `Ctrl+A` | Select all |
| `t` | This month |
| `y` | This year |
| `a` | All time |
| `←` / `→` | Previous/next period |

For the complete list of keyboard shortcuts, see [Keyboard Shortcuts](keyboard-shortcuts.md).
