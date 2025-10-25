# Category Configuration

## Overview

moneyflow uses Monarch Money's default category structure. You can customize categories via `~/.moneyflow/categories.yaml`.

## Quick Start

**View your current category structure:**
```bash
moneyflow categories dump              # YAML format (copy-pastable)
moneyflow categories dump --format=readable  # Human-readable with counts
```

**Customize categories:**
1. Run `moneyflow categories dump > my-categories.yaml`
2. Edit to add/remove categories as needed
3. Copy relevant sections to `~/.moneyflow/categories.yaml`
4. Run `moneyflow categories dump` to verify changes

## Configuration Format

```yaml
version: 1

# Rename group names (e.g., "Travel & Lifestyle" → "Travel")
rename_groups:
  "Health & Wellness": "Health & Fitness"

# Rename individual categories (match your Monarch account)
rename_categories:
  "Student Loans": "Student Loan Payments"

# Add custom categories to existing groups
add_to_groups:
  Business:
    - Accounting
    - Business Software

  Shopping:
    - Video Games
    - Books

# Create entirely new custom groups
custom_groups:
  Services:
    - Streaming
    - "Laundry & Dry Cleaning"
    - Software

# Move categories between groups
move_categories:
  "Internet & Cable": Services  # Default: Bills & Utilities
  Pets: "Health & Fitness"      # Default: Travel & Lifestyle
```

## Processing Order

Transformations are applied in this order:
1. **rename_groups** - Renames entire groups
2. **rename_categories** - Renames individual categories
3. **add_to_groups** - Adds categories to groups
4. **custom_groups** - Creates new groups
5. **move_categories** - Moves categories between groups

## Use Cases

### Add custom categories
Your Monarch account may have custom categories not in the defaults:
```yaml
add_to_groups:
  Business:
    - "My Custom Category"
```

### Rename categories
Match category names to your account:
```yaml
rename_categories:
  "Groceries": "Grocery Shopping"
```

### Reorganize groups
Prefer different grouping than Monarch's defaults:
```yaml
rename_groups:
  "Travel & Lifestyle": Travel

move_categories:
  "Entertainment & Recreation": Entertainment
  Personal: Miscellaneous
```

### Create custom groups
Add entirely new groups for your workflow:
```yaml
custom_groups:
  "Personal Care":
    - Hair
    - Spa
    - Massage
```

## Defaults

Without `categories.yaml`, moneyflow uses Monarch Money's default categories (15 groups, ~60 categories). See `categories.yaml.example` for the complete structure.

## Troubleshooting

**Categories not appearing:**
- Check YAML syntax is valid
- Verify version: 1 is present
- Use `moneyflow categories dump` to see effective structure

**Warning messages:**
- Check log at `~/.moneyflow/moneyflow.log`
- Invalid group names or typos will be logged
