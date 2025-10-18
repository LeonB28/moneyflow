# moneyflow

**Terminal UI for personal finance power users**

Track spending, bulk edit transactions, and navigate your financial data at lightning speed. Supports personal finance platforms like Monarch Money or even analyzing your Amazon purchase history.

[![GitHub stars](https://img.shields.io/github/stars/wesm/moneyflow?style=social)](https://github.com/wesm/moneyflow/stargazers)

!!! tip "New: Amazon Purchase Analysis"
    Now you can import and analyze your Amazon purchase history! [Learn more →](guide/amazon-mode.md)

```bash
# Install and run
pip install moneyflow
moneyflow

# Or run directly with uvx (no install needed)
uvx moneyflow
uvx moneyflow --demo  # Try with demo data

# NEW: Analyze Amazon purchases
moneyflow amazon import ~/Downloads/purchases.csv
moneyflow amazon
```

![moneyflow terminal UI](images/home-screen.png)

<div class="quick-links" markdown>
[Get Started](getting-started/installation.md){ .md-button .md-button--primary }
[Try Demo](getting-started/quickstart.md){ .md-button }
[View on GitHub](https://github.com/wesm/moneyflow){ .md-button }
</div>

---

## Who Is This For?

moneyflow is perfect if you:

- ✨ **Live in the terminal** - Prefer keyboard-driven workflows over clicking through web UIs
- 🚀 **Have lots of transactions to clean up** - Need to rename dozens of merchants or recategorize hundreds of transactions
- 🔍 **Want to analyze spending patterns** - Quickly drill down by merchant, category, or time period
- 📊 **Track Amazon purchases** - Want insights into your Amazon spending habits
- 🔒 **Value privacy** - Prefer local data processing over cloud-only platforms

---

## Why Choose moneyflow?

**Speed** - Edit hundreds of transactions in seconds. No page loads, no clicking through forms.

**Control** - All data processing happens locally. Review every change before syncing.

**Flexibility** - Works with Monarch Money, Amazon purchase history, or demo data. Extensible backend system.

**Privacy** - Credentials encrypted locally. No additional cloud services or third-party tracking.

---

## Features

<div class="feature-grid" markdown>

<div class="feature-card" markdown>
### Keyboard-Driven
Navigate, filter, and edit without touching the mouse. Vim-inspired shortcuts make common operations instant.
</div>

<div class="feature-card" markdown>
### Fast Local Operations
Download transactions once. All filtering, searching, and aggregation happens locally using Polars—no API latency.
</div>

<div class="feature-card" markdown>
### Bulk Editing
Select multiple transactions. Rename merchants or recategorize hundreds of transactions with a few keystrokes.
</div>

<div class="feature-card" markdown>
### Smart Views
Aggregate by merchant, category, group, or account. Drill down to individual transactions. Navigate time periods with arrow keys.
</div>

<div class="feature-card" markdown>
### Secure Credentials
Local credential storage with AES-128 encryption. Your finance credentials stay on your machine.
</div>

<div class="feature-card" markdown>
### Review Before Commit
See exactly what changes you're making before saving. All edits are queued and reviewed together.
</div>

</div>

---

## Quick Start

=== "Try Demo Mode"

    Perfect for exploring features before connecting your account:

    ```bash
    uvx moneyflow --demo
    ```

    No installation or account needed! Includes realistic synthetic data.

=== "Connect Monarch Money"

    For Monarch Money users:

    ```bash
    pip install moneyflow
    moneyflow
    ```

    First-run wizard guides you through credential setup. All credentials encrypted locally.

=== "Analyze Amazon Purchases"

    Import and explore your Amazon order history:

    **Step 1: Request your data from Amazon**

    1. Go to [Amazon Privacy Settings](https://www.amazon.com/gp/privacycentral/dsar/preview.html)
    2. Click "Request your Personal Information"
    3. Select "Your Orders" (uncheck other items)
    4. Submit request - Amazon will email you when ready (usually 1-2 days)
    5. Download the CSV file when ready

    <!-- TODO: Document exact CSV format and column mapping once official Amazon export support is added -->

    **Step 2: Import and analyze**

    ```bash
    pip install moneyflow
    moneyflow amazon import ~/Downloads/amazon-orders.csv
    moneyflow amazon
    ```

    Currently works with personal purchase CSV files. Official Amazon export format support coming soon!

---

## Common Use Cases

<div class="use-case-grid" markdown>

!!! example "Monthly Spending Review"
    Press ++t++ for this month → ++g++ to group by category → ++enter++ to drill into details. Navigate months with ++arrow-left++ / ++arrow-right++.

!!! example "Clean Up Merchant Names"
    Press ++g++ for merchant view → Select messy merchant → ++m++ to rename → All transactions updated instantly.

!!! example "Bulk Recategorization"
    Press ++u++ for all transactions → ++space++ to multi-select → ++c++ to recategorize → ++w++ to review → Commit!

!!! example "Find Duplicate Charges"
    Press ++D++ to see potential duplicates → Review side-by-side → Delete or keep as needed.

!!! example "Analyze Amazon Spending"
    Import CSV → Press ++g++ to group by category or item → See where your money really goes.

</div>

---

## Core Workflows

**View and analyze spending:**

- ++g++ - Cycle between merchant/category/group/account views
- ++u++ - Show all transactions
- ++slash++ - Search by merchant or category
- ++arrow-left++ ++arrow-right++ - Navigate time periods

**Edit transactions:**

- ++m++ - Rename merchant
- ++r++ - Recategorize
- ++h++ - Hide/unhide from reports
- ++space++ - Select multiple (bulk operations)

**Review and save:**

- ++w++ - Review pending changes
- ++c++ - Confirm and commit to backend

[Full keyboard reference →](guide/keyboard-shortcuts.md)

---

## Platform Support

**Currently supported:**

- **[Monarch Money](https://www.monarchmoney.com/)** - Full-featured integration with real-time sync
- **Amazon Purchase History** - Import and analyze your Amazon order history from CSV exports
- **Demo Mode** - Realistic synthetic data for testing features

**Coming soon:**

- YNAB (You Need A Budget)
- Lunch Money
- Generic CSV import for any platform

The backend system is pluggable—adding new platforms is straightforward. See [Contributing](development/contributing.md) if you want to add support for your platform.

[Learn more about Amazon Mode →](guide/amazon-mode.md)

---

## Installation

```bash
# Quick install
pip install moneyflow

# Or use uvx (no installation needed!)
uvx moneyflow --demo
```

**Requirements:** Python 3.11+

**Next steps:**

1. [📚 Full installation guide](getting-started/installation.md) - Detailed setup instructions
2. [🚀 Quick start guide](getting-started/quickstart.md) - Get up and running in 2 minutes
3. [⌨️ Keyboard shortcuts](guide/keyboard-shortcuts.md) - Master the interface

---

## Independent Open Source Project 

!!! info ""
    moneyflow is an independent open-source project. It is not affiliated with, endorsed by, or officially connected to Monarch Money, Inc. or any other finance platform.

---

## License

MIT License - see [LICENSE](https://github.com/wesm/moneyflow/blob/main/LICENSE) for details.
