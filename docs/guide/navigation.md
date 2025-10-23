# Navigation & Search

moneyflow provides multiple views of your transaction data and powerful search capabilities to find what you need quickly.

## View Types

### Aggregate Views

**Merchant View** (Press `m`)

- Shows spending grouped by merchant
- Columns: Merchant name, Transaction count, Total amount
- Sort by count, amount, or merchant name
- Press `Enter` to drill down to individual transactions

**Category View** (Press `c`)

- Shows spending grouped by category
- See which categories consume your budget
- Quick way to spot overspending
- Press `Enter` to view transactions in that category

**Group View** (Press `g`)

- High-level view of category groups
- Examples: Food & Dining, Travel, Housing, Income
- Best for monthly budget reviews
- Press `Enter` to see transactions in that group

**Account View** (Press `a`)

- Spending per bank account or credit card
- Useful for reconciliation
- Track per-account cash flow
- Press `Enter` to view transactions for that account

### Detail View

Press `d` to view individual transactions with all fields:

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

When drilled down, you can view sub-aggregations. For example:

```
Category View → Enter on "Groceries"
    ↓
Detail View (Groceries transactions)
    ↓ (Press 'm')
Merchant View (grouped by merchant, filtered to Groceries)
    ↓ (Press 'c')
Category View (returns to top-level categories)
```

This lets you answer questions like "Which merchants did I spend the most on for groceries?"

## Sorting

Press `s` to cycle through sort options. Available sort fields depend on the current view:

**Aggregate Views**:
- Field name (e.g., Merchant, Category)
- Count (number of transactions)
- Amount (total spending)

**Detail Views**:
- Date
- Merchant
- Category
- Account
- Amount

Press `r` to reverse sort direction (ascending/descending).

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
- Or press `Escape` while search is active

## Multi-Select

Select multiple transactions or groups for bulk operations:

- Press `Space` to select the current row
- Press `Ctrl+A` to select all visible items
- Selected items show a checkmark indicator
- Perform bulk edits (merchant rename, category change, hide/unhide)

## Time Navigation

Filter transactions by time period. See [Time Navigation](time-navigation.md) for details.

## Quick Reference

| Key | Action |
|-----|--------|
| `m` | Merchant view |
| `c` | Category view |
| `g` | Group view |
| `a` | Account view |
| `d` | Detail view |
| `Enter` | Drill down to details |
| `Escape` | Go back to previous view |
| `s` | Cycle sort field |
| `r` | Reverse sort direction |
| `/` | Search |
| `f` | Filters (transfers, hidden) |
| `Space` | Select current row |
| `Ctrl+A` | Select all |

For the complete list of keyboard shortcuts, see [Keyboard Shortcuts](keyboard-shortcuts.md).
