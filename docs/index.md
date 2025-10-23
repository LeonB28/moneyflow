# moneyflow [![GitHub stars](https://img.shields.io/github/stars/wesm/moneyflow?style=social)](https://github.com/wesm/moneyflow/stargazers)

**Terminal UI for personal finance power users**

![moneyflow terminal UI](https://raw.githubusercontent.com/wesm/moneyflow-assets/main/home-screen.png)

```bash
# Install and run
pip install moneyflow
moneyflow

# Or run directly with uvx (no install needed)
uvx moneyflow
uvx moneyflow --demo  # Try with demo data
```

Track spending, bulk edit transactions, and navigate your financial data at lightning speed. Supports personal finance platforms like Monarch Money or even analyzing your Amazon purchase history.

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
### Rapid Data Refinement
Select multiple transactions. Rename merchants or recategorize hundreds of transactions with a few keystrokes.
</div>

<div class="feature-card" markdown>
### Smart Views & Drill-Down
Aggregate by merchant, category, group, or account. Drill down and sub-group within any view—see your Amazon purchases by category, or your Groceries spending by merchant.
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

## Core Workflows

**View and analyze spending:**

- ++g++ - Cycle between merchant/category/group/account views
- ++u++ - Show all transactions
- ++slash++ - Search by merchant or category
- ++arrow-left++ ++arrow-right++ - Navigate time periods

**Edit transactions:**

- ++m++ - Rename merchant
- ++c++ - Edit category
- ++h++ - Hide/unhide from reports
- ++space++ - Select multiple (bulk operations)

**Review and save:**

- ++w++ - Review pending changes
- ++enter++ - Commit changes to backend

[Full keyboard reference →](guide/keyboard-shortcuts.md)

---

## Platform Support

**Currently supported:**

- **[Monarch Money](https://www.monarchmoney.com/)** - Full-featured integration with real-time sync
- **Amazon Purchase History** - Import and analyze your Amazon order history from official data exports
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
