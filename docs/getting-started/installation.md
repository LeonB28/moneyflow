# Installation

moneyflow can be installed in multiple ways depending on your preference.

## Quick Install

=== "pip (Recommended)"

    ```bash
    pip install moneyflow
    ```

    Then run:
    ```bash
    moneyflow
    ```

=== "uvx (No Install)"

    Try moneyflow without installing anything:

    ```bash
    uvx moneyflow
    ```

    Perfect for one-time use or trying before installing.

=== "pipx (Isolated)"

    Install in isolated environment:

    ```bash
    pipx install moneyflow
    ```

    Then run:
    ```bash
    moneyflow
    ```

---

## From Source

For developers or contributors:

```bash
# Clone the repository
git clone https://github.com/wesm/moneyflow.git
cd moneyflow

# Install dependencies with uv
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync

# Run from source
uv run moneyflow
```

---

## Requirements

- **Python 3.11+** (automatically handled by pip/uvx/pipx)
- **Terminal**: Any modern terminal with Unicode support
- **Account**: Monarch Money account (or use `--demo` mode)

---

## Verify Installation

```bash
# Check version
moneyflow --help

# Try demo mode (no account needed)
moneyflow --demo
```

If you see the demo data load successfully, you're all set!

---

## Next Steps

- [Quick Start Guide](quickstart.md) - Get up and running in 5 minutes
- [First Run Setup](first-run.md) - Configure Monarch Money credentials
- [Keyboard Shortcuts](../guide/keyboard-shortcuts.md) - Learn the keybindings

---

## Troubleshooting

Having issues? See the [Troubleshooting Guide](../reference/troubleshooting.md) for help.
