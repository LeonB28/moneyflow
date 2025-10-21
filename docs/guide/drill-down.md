# Drill-Down and Sub-Grouping

One of moneyflow's most powerful features is the ability to drill into any aggregated view and then sub-group the filtered data in different ways.

## Basic Drill-Down

From any aggregated view (Merchants, Categories, Groups, Accounts), press ++enter++ to drill into that item and see individual transactions.

![Drilled down into Amazon - transaction detail view](https://raw.githubusercontent.com/wesm/moneyflow-assets/main/drill-down-detail.png)

**Example:**

1. Start in Merchants view
2. Navigate to "Amazon"
3. Press ++enter++
4. See all Amazon transactions in detail view

The breadcrumb shows your current path: `Merchants > Amazon`

## Sub-Grouping Within Drill-Down

Once drilled down, press ++g++ to **sub-group** the filtered data instead of going back.

![Drilled into Amazon, grouped by Category](https://raw.githubusercontent.com/wesm/moneyflow-assets/main/drill-down-group-by-category.png)

**Example: Analyzing Amazon Purchases**

1. Drill into Merchant > Amazon
2. Press ++g++ then shows "Merchants > Amazon (by Category)"
   - See Amazon purchases grouped by category
3. Press ++g++ then shows "Merchants > Amazon (by Group)"
   - See Amazon purchases grouped by category group
4. Press ++g++ then shows "Merchants > Amazon (by Account)"
   - See which accounts you used for Amazon
5. Press ++g++ then back to detail view

![Drilled into Amazon, grouped by Account](https://raw.githubusercontent.com/wesm/moneyflow-assets/main/drill-down-group-by-account.png)

This answers questions like:

- "How much did I spend on groceries from Amazon?"
- "Which credit card do I use most at Starbucks?"
- "What categories make up my Target spending?"

## Multi-Level Drill-Down

You can drill down **from sub-grouped views** to add another filter level.

**Example: Amazon Groceries**

1. Merchant > Amazon
2. Press ++g++ until "(by Category)"
3. Press ++enter++ on "Groceries"
4. Breadcrumb shows: `Merchants > Amazon > Groceries`
5. See only Amazon grocery transactions

<!-- TODO: Add screenshot of multi-level drill-down breadcrumb -->

## Navigation with Sub-Grouping

### Press ++g++ - Cycle Sub-Groupings

When drilled down, ++g++ cycles through available sub-groupings. The field you're already filtered by is excluded from the cycle.

### Press ++escape++ - Go Back One Level

Escape navigates backwards through your drill-down path:

**Single-level with sub-grouping:**

1. `Merchants > Amazon (by Category)`
2. Press ++escape++ goes to `Merchants > Amazon` (clears sub-grouping)
3. Press ++escape++ goes to `Merchants` (clears drill-down)

**Multi-level:**

1. `Merchants > Amazon > Groceries`
2. Press ++escape++ goes to `Merchants > Amazon` (clears category)
3. Press ++escape++ goes to `Merchants` (clears merchant)

<!-- TODO: Add diagram showing navigation flow -->

### Press ++enter++ - Drill Deeper

From a sub-grouped view, press ++enter++ to add another filter level.

## Use Cases

### Analyze Spending by Store and Category

**Question:** "What do I buy at Costco?"

1. ++g++ to Merchants view
2. ++enter++ on "Costco"
3. ++g++ until "(by Category)"
4. See breakdown: Groceries $450, Gas $120, etc.

<!-- TODO: Add screenshot of Costco by Category breakdown -->

### Find Which Merchants for a Category

**Question:** "Where am I buying groceries?"

1. ++g++ to Categories view
2. ++enter++ on "Groceries"
3. ++g++ until "(by Merchant)"
4. See breakdown: Whole Foods $890, Safeway $650, Amazon $234

<!-- TODO: Add screenshot of Groceries by Merchant breakdown -->

### Review Spending Across Accounts

**Question:** "How do I use my Chase Sapphire card?"

1. ++g++ to Accounts view
2. ++enter++ on "Chase Sapphire"
3. ++g++ until "(by Category)"
4. See spending breakdown by category for that card

<!-- TODO: Add screenshot of account spending by category -->

## Tips

!!! tip "Quick Analysis"
    - ++g++ is your analysis tool when drilled down
    - Quickly pivot between different views of the same data
    - No need to go back and re-filter

!!! tip "Pending Edits Indicator"
    The `*` flag shows in sub-grouped views too, so you can see which sub-groups have uncommitted changes.

!!! tip "Combine with Time Navigation"
    - Press ++t++ for this month
    - Drill down and sub-group to analyze current spending
    - Press ++left++ to compare with previous months

## Summary

| Key | Action | Context |
|-----|--------|---------|
| ++enter++ | Drill down | Any aggregated row |
| ++g++ | Cycle sub-groupings | When drilled down |
| ++g++ | Cycle top-level views | When not drilled down |
| ++escape++ | Go back one level | Any drill-down or sub-grouping |

The drill-down and sub-grouping system lets you explore your data from multiple angles without losing context.
