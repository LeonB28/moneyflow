# Navigation & Search

moneyflow provides multiple views of your transaction data and powerful drill-down capabilities to analyze spending from different angles.

## View Types

### Aggregate Views

Press `g` to cycle through aggregate views. Aggregate views group transactions by a specific field and show counts and totals.

**Cycle Order**: Merchant → Category → Group → Account → Merchant...

<table>
<tr>
<td width="50%">
<strong>Merchant View</strong><br>
<img src="https://raw.githubusercontent.com/wesm/moneyflow-assets/main/cycle-1-merchants.png" width="100%">
</td>
<td width="50%">
<strong>Category View</strong><br>
<img src="https://raw.githubusercontent.com/wesm/moneyflow-assets/main/cycle-2-categories.png" width="100%">
</td>
</tr>
<tr>
<td width="50%">
<strong>Group View</strong><br>
<img src="https://raw.githubusercontent.com/wesm/moneyflow-assets/main/cycle-3-groups.png" width="100%">
</td>
<td width="50%">
<strong>Account View</strong><br>
<img src="https://raw.githubusercontent.com/wesm/moneyflow-assets/main/cycle-4-accounts.png" width="100%">
</td>
</tr>
</table>

**Merchant View**
- Groups transactions by merchant name
- Shows: Merchant, Count, Total
- Example: See all Amazon purchases totaled

**Category View**
- Groups by spending category
- Shows: Category, Count, Total
- Example: See total spent on "Groceries"

**Group View**
- Groups by high-level category groups
- Shows: Group, Count, Total
- Examples: Food & Dining, Travel, Housing, Income

**Account View**
- Groups by bank account or credit card
- Shows: Account, Count, Total
- Useful for reconciliation and per-account analysis

**Amazon Mode**: View names differ to reflect Amazon purchase data:
- Item (product names), Category (product categories), Order ID (group by order)
- Account view not available

### Detail View

Press `u` to view all transactions ungrouped, or press `Enter` from any aggregate row.

Shows individual transactions:
- Columns: Date, Merchant, Category, Account, Amount
- Indicators: ✓ (selected), H (hidden), * (pending edit)
- Full editing capabilities

![Detail view with indicators](https://raw.githubusercontent.com/wesm/moneyflow-assets/main/detail-view-flags.png)

## Drill-Down

From any aggregate view, press `Enter` to drill into that row and see its transactions.

![Merchant view with Amazon highlighted](https://raw.githubusercontent.com/wesm/moneyflow-assets/main/merchants-view.png)

**Example:**
1. Start in Merchant view
2. Navigate to "Amazon"
3. Press `Enter`
4. See all Amazon transactions

![Drilled down into Amazon - transaction detail view](https://raw.githubusercontent.com/wesm/moneyflow-assets/main/drill-down-detail.png)

The breadcrumb shows your path: `Merchants > Amazon`

## Sub-Grouping

Once drilled down, press `g` to sub-group the filtered data instead of returning to the top.

**Example - Analyzing Amazon purchases:**
1. Drill into Amazon (Merchant view → Enter)
2. Press `g` → see `Merchants > Amazon (by Category)`
3. Press `g` → see `Merchants > Amazon (by Group)`
4. Press `g` → see `Merchants > Amazon (by Account)`
5. Press `g` → back to detail view

![Drilled into Merchant, grouped by Category](https://raw.githubusercontent.com/wesm/moneyflow-assets/main/merchants-drill-by-category.png)

![Drilled into Amazon, grouped by Account](https://raw.githubusercontent.com/wesm/moneyflow-assets/main/drill-down-group-by-account.png)

This answers questions like:
- "How much did I spend on groceries from Amazon?"
- "Which credit card do I use most at Starbucks?"
- "What categories make up my Target spending?"

When drilled down, `g` cycles through sub-groupings. The field you're already filtered by is excluded from the cycle.

## Multi-Level Drill-Down

You can drill down from sub-grouped views to add another filter level.

**Example - Amazon Groceries:**
1. Merchant view → Enter on "Amazon"
2. Press `g` until "(by Category)"
3. Press `Enter` on "Groceries"
4. Breadcrumb shows: `Merchants > Amazon > Groceries`
5. See only Amazon grocery transactions

## Going Back

Press `Escape` to navigate backwards through your drill-down path.

**Single-level with sub-grouping:**
- `Merchants > Amazon (by Category)` → Escape → `Merchants > Amazon` (clears sub-grouping)
- `Merchants > Amazon` → Escape → `Merchants` (clears drill-down)

**Multi-level:**
- `Merchants > Amazon > Groceries` → Escape → `Merchants > Amazon` (clears category)
- `Merchants > Amazon` → Escape → `Merchants` (clears merchant)

**With search active:**
- `Search: starbucks` → Escape clears search first
- Subsequent Escape presses navigate through drill-down levels

Your cursor position and scroll state are preserved when going back.

## Sorting

Press `s` to cycle through sort fields. Press `v` to reverse direction.

**Aggregate Views**: Field name, Count, Amount
**Detail Views**: Date, Merchant, Category, Account, Amount

## Time Navigation

Filter transactions by time period.

**Quick Filters:**
- `t` - This month
- `y` - This year
- `a` - All time

**Navigate Periods:**
- `←` (Left) - Previous period
- `→` (Right) - Next period

When viewing "This Month", arrows move to previous/next month. When viewing "This Year", arrows move to previous/next year.

**Command-Line:**
```bash
moneyflow --year 2025    # Load only 2025
moneyflow --days 90      # Load last 90 days
moneyflow --month 2025-03  # Load March 2025
```

## Search

Press `/` to search across merchant, category, and notes fields.

![Search modal](https://raw.githubusercontent.com/wesm/moneyflow-assets/main/search-modal.png)

**Usage:**
1. Press `/` → search modal opens
2. Type query (case-insensitive, partial matching)
3. Press `Enter` → apply filter
4. Press `Escape` → clear search

![Search results for "coffee"](https://raw.githubusercontent.com/wesm/moneyflow-assets/main/merchants-search.png)

Search persists across view changes. Breadcrumb shows "Search: your query".

## Multi-Select

Select multiple rows for bulk operations:
- `Space` - Toggle current row
- `Ctrl+A` - Select all visible rows

Perform bulk edits: merchant rename, category change, hide/unhide.

## Common Use Cases

**"What do I buy at Costco?"**
1. Press `g` to Merchant view
2. Press `Enter` on "Costco"
3. Press `g` until "(by Category)"
4. See breakdown: Groceries $450, Gas $120, etc.

**"Where am I buying groceries?"**
1. Press `g` to Category view
2. Press `Enter` on "Groceries"
3. Press `g` until "(by Merchant)"
4. See breakdown: Whole Foods $890, Safeway $650, Amazon $234

**"How do I use my Chase Sapphire card?"**
1. Press `g` to Account view
2. Press `Enter` on "Chase Sapphire"
3. Press `g` until "(by Category)"
4. See spending breakdown by category for that card

**Quick Analysis:**
- `g` is your pivot tool when drilled down
- No need to go back and re-filter
- Combine with time navigation: `t` for this month, `←` for previous months

## Quick Reference

| Key | Action |
|-----|--------|
| `g` | Cycle views (Merchant/Category/Group/Account) |
| `u` | All transactions |
| `Enter` | Drill down |
| `Escape` | Go back |
| `s` | Cycle sort field |
| `v` | Reverse sort |
| `/` | Search |
| `f` | Filters |
| `Space` | Select row |
| `Ctrl+A` | Select all |
| `t` / `y` / `a` | Time filters |
| `←` / `→` | Previous/next period |

For all keyboard shortcuts, see [Keyboard Shortcuts](keyboard-shortcuts.md).
