<div class="hero">

<div class="hero-content">

# moneyflow

**Terminal UI for personal finance power users**

Track spending, bulk edit transactions, and navigate your financial data at keyboard speed.

```bash
pip install moneyflow
moneyflow
```

Monarch Money • Python 3.11+

</div>

<div class="hero-screenshot">
<!-- Replace this div with: <img src="images/screenshot.png" alt="moneyflow TUI"> -->
<div class="screenshot-placeholder">
  <p>Screenshot</p>
  <p>Coming Soon</p>
</div>
</div>

</div>

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

```bash
# Try with demo data
uvx moneyflow --demo

# Run with your Monarch Money account
moneyflow

# Load recent transactions only (faster startup)
moneyflow --mtd         # Month-to-date
moneyflow --year 2025   # Year to present
```

On first run, you'll configure your finance platform credentials. They're encrypted and stored locally at `~/.moneyflow/`.

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

- [Monarch Money](https://www.monarchmoney.com/) - Full support

**Planned:**

- YNAB (You Need A Budget)
- Lunch Money
- Generic CSV import

The backend system is pluggable—adding new platforms is straightforward. See [Contributing](development/contributing.md) if you want to add support for your platform.

---

## Installation

```bash
# Using pip
pip install moneyflow

# Using uv (recommended)
uv tool install moneyflow

# Try without installing
uvx moneyflow --demo
```

**Requirements:** Python 3.11+

[Installation guide →](getting-started/installation.md)

---

## Not Affiliated

!!! info ""
    moneyflow is an independent open-source project. It is not affiliated with, endorsed by, or officially connected to Monarch Money, Inc. or any other finance platform.

---

## License

MIT License - see [LICENSE](https://github.com/wesm/moneyflow/blob/main/LICENSE) for details.
