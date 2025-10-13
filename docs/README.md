# moneyflow Documentation

This directory contains the source for the moneyflow documentation site at [moneyflow.dev](https://moneyflow.dev).

## Local Development

### Preview the site locally:

```bash
# Install docs dependencies
uv sync --group docs

# Serve locally with live reload
uv run mkdocs serve

# Open http://127.0.0.1:8000 in your browser
```

### Build the site:

```bash
uv run mkdocs build

# Output in site/ directory
```

## Deployment

Documentation is automatically deployed to GitHub Pages when changes are pushed to `main`:

1. Push changes to `main` branch
2. GitHub Actions builds the site
3. Deploys to `gh-pages` branch
4. Available at https://moneyflow.dev (after DNS setup)

## Adding Screenshots

Screenshots should be stored in the separate `moneyflow-assets` repository and referenced via URL:

```markdown
![Description](https://raw.githubusercontent.com/wesm/moneyflow-assets/main/screenshots/example.png)
```

This keeps the main repository lightweight.

## Structure

```
docs/
├── index.md                  # Landing page
├── getting-started/          # Installation, quickstart, first run
├── guide/                    # User guides (keyboard shortcuts, views, etc.)
├── config/                   # Configuration docs
├── reference/                # CLI reference, troubleshooting, FAQ
├── development/              # Contributing, architecture, testing
└── stylesheets/              # Custom CSS for terminal aesthetic
```

## Style Guide

- Use dark terminal aesthetic (see terminal.css)
- Include code examples for every feature
- Use admonitions for tips/warnings/notes
- Keep language concise and technical
- Keyboard shortcuts use ++key++ syntax
