# Category Configuration

## Overview

moneyflow includes a built-in category structure (~60 categories in 15 groups) chosen to ease integration with Monarch Money. The category hierarchy is fully customizable via `~/.moneyflow/config.yaml`.

**Common use cases:**
- Add custom categories from your finance platform
- Rename groups or categories to match your workflow
- Reorganize categories into different groups
- Create entirely new custom groups

**File location:** `~/.moneyflow/config.yaml` (optional - defaults work out of the box)

## Quick Start

**View your current category hierarchy:**
```bash
moneyflow categories dump              # YAML format (copy-pastable)
moneyflow categories dump --format=readable  # Human-readable with counts
```

**Create your configuration:**
```bash
# Option 1: Start from example
cp config.yaml.example ~/.moneyflow/config.yaml

# Option 2: Dump current hierarchy and customize
moneyflow categories dump > my-categories.yaml
# Edit my-categories.yaml, then copy to ~/.moneyflow/config.yaml under 'categories:' section
```

**Verify your changes:**
```bash
moneyflow categories dump
```

## Configuration Format

All sections are optional. Transformations are applied in the order shown below.

```yaml
version: 1  # Required

categories:
  # 1. Rename entire groups (renames the group and all its categories)
  rename_groups:
    "Travel & Lifestyle": Travel
    "Health & Wellness": "Health & Fitness"

  # 2. Rename individual categories
  rename_categories:
    "Student Loans": "Student Loan Payments"
    "Groceries": "Grocery Shopping"

  # 3. Add custom categories to existing groups
  #    Use this for categories from your finance platform
  add_to_groups:
    Business:
      - Accounting
      - Business Software
    Shopping:
      - Video Games
      - Books

  # 4. Create new custom groups
  #    Use this for categories that don't fit any default group
  custom_groups:
    Services:
      - Streaming
      - "Laundry & Dry Cleaning"
      - Software

  # 5. Move categories to different groups
  #    Overrides the default group assignment
  move_categories:
    "Internet & Cable": Services     # Built-in default: Bills & Utilities
    Pets: "Health & Fitness"         # Built-in default: Travel & Lifestyle
```

## Common Scenarios

### Scenario 1: Add Custom Categories

Your finance platform has categories not in the built-in defaults:

```yaml
categories:
  add_to_groups:
    Business:
      - "Contractor Payments"
      - "Business Insurance"
    Shopping:
      - "Video Games"
```

### Scenario 2: Reorganize to Match Your Preferences

Create a custom group and move categories:

```yaml
categories:
  custom_groups:
    "Personal Care":
      - Hair
      - Spa

  move_categories:
    "Laundry & Dry Cleaning": "Personal Care"
```

### Scenario 3: Rename to Match Your Platform

Match category names to your finance platform:

```yaml
categories:
  rename_categories:
    "Groceries": "Grocery Shopping"
    "Student Loans": "Student Loan Payments"
```

### Scenario 4: Simplify Group Names

```yaml
categories:
  rename_groups:
    "Travel & Lifestyle": Travel
    "Gifts & Donations": Gifts
```

## Built-in Defaults

Without `config.yaml`, moneyflow uses built-in categories chosen to ease integration with Monarch Money:

- **15 groups**: Income, Gifts & Donations, Auto & Transport, Housing, Bills & Utilities, Food & Dining, Travel & Lifestyle, Shopping, Children, Education, Health & Wellness, Financial, Uncategorized, Business, Transfers
- **~60 categories**: Groceries, Restaurants & Bars, Gas, Shopping, Medical, etc.

**These defaults work well for most personal finance platforms.** Customize as needed for your workflow.

See `config.yaml.example` in the repo for the complete structure.

## Troubleshooting

**Issue**: Categories not showing in the UI

**Solutions**:
1. Verify YAML syntax: `moneyflow categories dump`
2. Check version field is `1`
3. Check logs: `~/.moneyflow/moneyflow.log` (search for "categories")

**Issue**: Warning messages about invalid groups

**Solutions**:
- Typo in group name (case-sensitive)
- Trying to add to non-existent group (create it with `custom_groups` first)
- Group was renamed (use new name after `rename_groups`)

**Tip**: Use `moneyflow categories dump --format=readable` to see your effective category structure with group counts.
