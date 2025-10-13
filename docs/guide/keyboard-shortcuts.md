# Keyboard Shortcuts

moneyflow is designed to be used entirely with the keyboard. Here's your complete reference.

---

## Essential Shortcuts

| Key | Action | Context |
|-----|--------|---------|
| ++question++ | Show help screen | Any |
| ++q++ | Quit (with confirmation) | Any |
| ++ctrl+c++ | Force quit | Any |
| ++w++ | Review & commit changes | Any |

---

## View Navigation

### Cycle Through Views

| Key | Action |
|-----|--------|
| ++g++ | Cycle grouping (Merchant → Category → Group → Account) |
| ++u++ | All transactions (ungrouped detail view) |
| ++d++ | Find duplicates |

### Direct View Access

| Key | View |
|-----|------|
| ++c++ | Categories (hidden shortcut) |
| ++shift+a++ | Accounts (hidden shortcut) |

### Drill Down

| Key | Action |
|-----|--------|
| ++enter++ | Drill down into selected row |
| ++escape++ | Go back to previous view |

---

## Time Navigation

### Quick Jumps

| Key | Time Period |
|-----|-------------|
| ++y++ | Current year |
| ++t++ | Current month (Today's month) |
| ++a++ | All time |

### Specific Months

| Key | Month |
|-----|-------|
| ++1++ | January |
| ++2++ | February |
| ++3++ | March |
| ++4++ | April |
| ++5++ | May |
| ++6++ | June |
| ++7++ | July |
| ++8++ | August |
| ++9++ | September |

!!! tip "Quick Access"
    Press ++5++ to jump to May of the current year instantly.

### Period Navigation

| Key | Action |
|-----|--------|
| ++left++ | Previous period (month or year) |
| ++right++ | Next period (month or year) |

**Smart navigation**: If viewing a full year, arrows move by year. If viewing a month, arrows move by month.

---

## Editing Transactions

!!! info "Detail View Only"
    These shortcuts only work when viewing individual transactions (not in aggregate views).

### Single Transaction

| Key | Action |
|-----|--------|
| ++m++ | Edit merchant name |
| ++r++ | Recategorize |
| ++h++ | Hide/unhide from reports |
| ++d++ | Delete (with confirmation) |
| ++i++ | View full transaction details |

### Multi-Select

| Key | Action |
|-----|--------|
| ++space++ | Toggle selection (shows ✓) |
| ++m++ | Edit merchant for all selected |
| ++r++ | Recategorize all selected |
| ++h++ | Hide/unhide all selected |

!!! example "Bulk Workflow"
    1. Press ++space++ on multiple transactions (shows ✓)
    2. Press ++r++ to recategorize them all
    3. Select new category
    4. Press ++w++ to review
    5. Press ++c++ to commit

---

## Bulk Edit from Aggregate View

When viewing **Merchants** aggregate:

| Key | Action |
|-----|--------|
| ++m++ | Edit merchant for ALL transactions in that merchant |
| ++enter++ | Drill down to see individual transactions |

This lets you rename a merchant across hundreds of transactions in one operation.

---

## Sorting

| Key | Action | Context |
|-----|--------|---------|
| ++s++ | Toggle sort field | Any view |
| ++v++ | Reverse sort direction (↑/↓) | Any view |

**In aggregate views** (Merchant/Category/Group):
- ++s++ toggles between Count and Amount

**In detail view** (transactions):
- ++s++ cycles through: Date → Merchant → Category → Account → Amount → Date

---

## Search & Filters

| Key | Action |
|-----|--------|
| ++slash++ | Search transactions |
| ++f++ | Show filter modal (transfers, hidden items) |

### In Search Modal

- **Type** to filter in real-time
- ++enter++ to apply search
- ++escape++ to cancel

---

## Arrow Key Navigation

| Key | Action |
|-----|--------|
| ++up++ / ++k++ | Move cursor up |
| ++down++ / ++j++ | Move cursor down |
| ++page-up++ | Jump up multiple rows |
| ++page-down++ | Jump down multiple rows |
| ++home++ | Jump to top |
| ++end++ | Jump to bottom |

---

## Workflow Shortcuts

### Common Workflows

**Rename a merchant:**

1. ++g++ (until Merchants view)
2. Navigate to merchant
3. ++m++ (edit merchant)
4. Type new name, ++enter++
5. ++w++ (review), ++c++ (commit)

**Recategorize transactions:**

1. ++u++ (all transactions)
2. ++space++ on each transaction to select
3. ++r++ (recategorize)
4. Type to filter categories, ++enter++ to select
5. ++w++ (review), ++c++ (commit)

**Monthly spending review:**

1. ++t++ (this month)
2. ++g++ (cycle to categories)
3. ++enter++ on a category to drill down
4. ++left++ to view previous month
5. ++right++ to return

---

## In-Modal Shortcuts

When in a modal dialog (edit merchant, select category, etc.):

| Key | Action |
|-----|--------|
| ++enter++ | Confirm/Submit |
| ++escape++ | Cancel |
| ++tab++ | Next field |
| ++shift+tab++ | Previous field |
| ++up++ / ++down++ | Navigate list items |

### Category Selector

- **Type** to filter categories in real-time
- ++up++ / ++down++ to navigate matches
- ++enter++ to select

---

## Pro Tips

!!! tip "Speed Up Editing"
    - Stay in detail view (++u++) for rapid transaction editing
    - Use ++space++ to queue multiple edits before committing
    - The cursor stays in place after edits - keep pressing ++m++ or ++r++

!!! tip "Time Navigation"
    - Use ++1++-++9++ for instant month access
    - ++left++/++right++ maintain context (month→month, year→year)
    - ++y++ is your "reset" - always returns to current year

!!! tip "Review Before Committing"
    - ++w++ shows ALL pending changes before saving
    - Review screen shows old → new values
    - Press ++escape++ to cancel, ++c++ to confirm

---

## Cheat Sheet

Print this for reference:

```
Views:       g (cycle)  u (all)  D (duplicates)
Time:        y (year)   t (month)  a (all)  ←/→ (navigate)
Edit:        m (merchant)  r (category)  h (hide)  d (delete)
Select:      Space (multi-select)
Sort:        s (toggle field)  v (reverse)
Other:       / (search)  f (filter)  w (commit)  ? (help)  q (quit)
```

---

## Can't Remember a Shortcut?

Press ++question++ any time to see the help screen with all available shortcuts for your current view.
