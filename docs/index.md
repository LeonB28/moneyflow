# moneyflow

<div class="hero" markdown>

# moneyflow

<p class="tagline">$ track your moneyflow</p>

**A blazing-fast terminal UI for personal finance power users.**

Built for speed. Designed for keyboards. Made for people who think in transactions per second, not clicks per minute.

**Currently supports**: Monarch Money • More platforms coming soon

<div class="install-command">
pip install moneyflow
</div>

[Get Started](getting-started/installation.md){ .md-button .md-button--primary }
[Try Demo](getting-started/quickstart.md#demo-mode){ .md-button }
[View on GitHub](https://github.com/wesm/moneyflow){ .md-button }

</div>

---

## Why moneyflow?

<div class="feature-grid" markdown>

<div class="feature-card" markdown>
### ⚡ Blazing Fast
Download all transactions once. Filter, search, and aggregate **instantly** using Polars. No waiting for API calls.
</div>

<div class="feature-card" markdown>
### ⌨️ Keyboard-First
Zero mouse required. Vim-inspired shortcuts. Navigate your finances at the speed of thought.
</div>

<div class="feature-card" markdown>
### 🎯 Bulk Operations
Multi-select transactions. Batch rename merchants. Recategorize hundreds of transactions in seconds.
</div>

<div class="feature-card" markdown>
### 🔐 Secure
AES-128 encryption with PBKDF2 (100k iterations). Your credentials never leave your machine.
</div>

<div class="feature-card" markdown>
### 📊 Smart Aggregation
View by merchant, category, or group. Drill down to transactions. See your spending patterns instantly.
</div>

<div class="feature-card" markdown>
### 🎮 Demo Mode
Try it risk-free with synthetic data. No account needed. Perfect for learning or showcasing.
</div>

</div>

---

## Quick Look

```bash
# Install
pip install moneyflow

# Or try instantly with uvx (no installation!)
uvx moneyflow --demo

# Run with your Monarch Money account
moneyflow

# Load only recent data
moneyflow --year 2025
```

**First time?** The app walks you through encrypted credential setup for your finance platform.

---

## What You Can Do

### View Your Spending

- **By Merchant**: See which stores you spend the most at
- **By Category**: Track groceries, dining, travel separately
- **By Group**: High-level view (Food & Dining, Travel, Housing)
- **By Account**: Per credit card or bank account
- **All Transactions**: Chronological list with full details

### Edit Efficiently

- **Rename merchants**: Fix "AMZN*ABC123" → "Amazon"
- **Recategorize**: Move transactions to correct categories
- **Bulk operations**: Select multiple, edit once
- **Hide from reports**: Mark transfers and one-offs
- **Review before commit**: See all changes before saving

### Navigate Time

- Jump to any month (++1++ through ++9++)
- Navigate years with arrow keys
- Filter to current month/year instantly
- View all-time or custom ranges

### Search & Filter

- Type ++slash++ to search by merchant or category
- Filter out transfers and hidden items
- Live filtering as you type
- Combine filters for precise views

---

## Built With

<div class="metrics">
<div class="metric">
  <div class="metric-value">334</div>
  <div class="metric-label">Tests Passing</div>
</div>
<div class="metric">
  <div class="metric-value">61%</div>
  <div class="metric-label">Code Coverage</div>
</div>
<div class="metric">
  <div class="metric-value">0ms</div>
  <div class="metric-label">Filter Latency</div>
</div>
</div>

**Stack**: Python 3.11+ • [Textual](https://textual.textualize.io/) • [Polars](https://pola.rs/) • Pluggable Backend System

---

## Screenshots

!!! note "Screenshots Coming Soon"
    Beautiful terminal screenshots will be added here once we set up the moneyflow-assets repository.

    For now, try it yourself: `uvx moneyflow --demo`

---

## Not Affiliated

!!! warning "Independent Project"
    moneyflow is an **independent open-source project** and is not affiliated with, endorsed by, or officially connected to Monarch Money, Inc.

    Monarch Money® is a trademark of Monarch Money, Inc.

---

## Ready to Start?

<div style="text-align: center; margin: 3rem 0;">

[Install moneyflow](getting-started/installation.md){ .md-button .md-button--primary style="font-size: 1.2em; padding: 1em 2em;" }

</div>
