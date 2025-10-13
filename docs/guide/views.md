# Views & Navigation

moneyflow provides multiple views of your transaction data. Learn how to navigate between them efficiently.

## View Types

### Aggregate Views

**Merchant View**

- Shows spending grouped by merchant
- Columns: Merchant name, Transaction count, Total amount
- Sort by count or amount
- Press ++enter++ to drill down to individual transactions

**Category View**

- Shows spending grouped by category
- See which categories consume your budget
- Quick way to spot overspending

**Group View**

- High-level view of category groups
- Examples: Food & Dining, Travel, Housing
- Best for monthly budget reviews

**Account View**

- Spending per bank account or credit card
- Useful for reconciliation
- Track per-account cash flow

### Detail View

Shows individual transactions with all fields:

- Date, Merchant, Category, Account, Amount
- Visual indicators: ✓ (selected), H (hidden), * (pending edit)
- Full editing capabilities

## Navigation Patterns

```
Merchant View
    ↓ (Enter on "Amazon")
Transaction Detail View (filtered to Amazon)
    ↓ (Escape)
Merchant View (cursor restored)
```

[Full documentation coming soon]
