# Advanced Configuration

## Category Customization

Customize the category hierarchy to match your Monarch Money account.

**📁 Configuration file:** `~/.moneyflow/categories.yaml`

**Quick commands:**
```bash
moneyflow categories dump              # View current hierarchy (YAML format)
moneyflow categories dump --format=readable  # View with counts
```

**Features:**
- Add custom categories from your Monarch account
- Rename groups or categories
- Reorganize categories into different groups
- Create custom groups

**See:** [Category Configuration Guide](../categories.md) for complete documentation.

## Data Caching

Speed up startup by caching transaction data locally.

**Usage:**
```bash
moneyflow --cache              # Enable caching (uses ~/.moneyflow/cache/)
moneyflow --cache ~/my-cache   # Custom cache location
moneyflow --refresh            # Force refresh, skip cache
```

**See:** [Caching Guide](caching.md) for details.

## Configuration Directory

All moneyflow configuration is stored in `~/.moneyflow/`:

```
~/.moneyflow/
├── categories.yaml    # Category customization (optional)
├── credentials.enc    # Encrypted Monarch credentials
├── salt               # Encryption salt
├── merchants.json     # Merchant name cache
├── cache/             # Transaction cache (if --cache enabled)
└── moneyflow.log      # Application logs
```

**Security note:** credentials.enc is encrypted with AES-128. Safe to backup but keep private.
