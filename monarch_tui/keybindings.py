"""
Centralized keyboard shortcuts and help text for Monarch TUI.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class KeyBinding:
    """A keyboard shortcut definition."""

    key: str
    action: str
    description: str
    category: str


# All keyboard shortcuts organized by category
KEYBINDINGS: List[KeyBinding] = [
    # Navigation
    KeyBinding("m", "view_merchants", "View merchant aggregation", "Navigation"),
    KeyBinding("c", "view_categories", "View category aggregation", "Navigation"),
    KeyBinding("g", "view_groups", "View category group aggregation", "Navigation"),
    KeyBinding("↑/k", "up", "Move cursor up", "Navigation"),
    KeyBinding("↓/j", "down", "Move cursor down", "Navigation"),
    KeyBinding("←/h", "toggle_sort", "Toggle sort: amount ↔ date", "Navigation"),
    KeyBinding("→/l", "toggle_sort", "Toggle sort: amount ↔ date", "Navigation"),
    KeyBinding("enter", "drill_down", "Drill down / Edit selected", "Navigation"),
    KeyBinding("esc", "go_back", "Go back / Cancel", "Navigation"),
    KeyBinding("gg", "jump_top", "Jump to top (vim-style)", "Navigation"),
    KeyBinding("G", "jump_bottom", "Jump to bottom (vim-style)", "Navigation"),
    # Time Frames
    KeyBinding("1-9", "select_month", "Select month (1=Jan, 2=Feb, etc.)", "Time"),
    KeyBinding("y", "this_year", "View this year", "Time"),
    KeyBinding("a", "all_time", "View all time", "Time"),
    KeyBinding("<", "prev_period", "Previous period", "Time"),
    KeyBinding(">", "next_period", "Next period", "Time"),
    # Actions
    KeyBinding("space", "toggle_select", "Multi-select for bulk edit", "Actions"),
    KeyBinding("e", "edit_merchant", "Edit merchant name", "Actions"),
    KeyBinding("r", "edit_category", "Change category (r=recategorize)", "Actions"),
    KeyBinding("H", "toggle_hide", "Toggle hide from reports", "Actions"),
    KeyBinding("d", "delete", "Delete transaction (with confirmation)", "Actions"),
    KeyBinding("/", "search", "Fuzzy search/filter", "Actions"),
    KeyBinding("n", "next_match", "Next search result", "Actions"),
    KeyBinding("N", "prev_match", "Previous search result", "Actions"),
    # Bulk Operations
    KeyBinding("E", "bulk_edit_merchant", "Bulk edit merchant name", "Bulk"),
    KeyBinding("C", "bulk_categorize", "Bulk change category", "Bulk"),
    KeyBinding("shift+H", "bulk_toggle_hide", "Bulk toggle hide from reports", "Bulk"),
    KeyBinding("u", "undo", "Undo last change", "Bulk"),
    KeyBinding("ctrl+r", "redo", "Redo", "Bulk"),
    # System
    KeyBinding("ctrl+s", "save", "Save pending changes", "System"),
    KeyBinding(":w", "save", "Save pending changes (vim-style)", "System"),
    KeyBinding("q", "quit", "Quit (warn if unsaved)", "System"),
    KeyBinding(":q", "quit", "Quit (vim-style)", "System"),
    KeyBinding(":wq", "save_quit", "Save and quit", "System"),
    KeyBinding("ctrl+l", "refresh", "Refresh from API", "System"),
    KeyBinding(":export", "export_csv", "Export to CSV", "System"),
    KeyBinding("?", "help", "Show this help screen", "System"),
]


def get_help_text() -> str:
    """Generate formatted help text for all keybindings."""
    # Group by category
    categories = {}
    for binding in KEYBINDINGS:
        if binding.category not in categories:
            categories[binding.category] = []
        categories[binding.category].append(binding)

    # Format as text
    lines = ["Monarch Money TUI - Keyboard Shortcuts", "=" * 60, ""]

    for category in ["Navigation", "Time", "Actions", "Bulk", "System"]:
        if category in categories:
            lines.append(f"{category}:")
            lines.append("-" * 40)
            for binding in categories[category]:
                # Pad key to 15 chars
                key_display = f"  {binding.key:<15}"
                lines.append(f"{key_display} {binding.description}")
            lines.append("")

    return "\n".join(lines)


def get_textual_bindings():
    """Get bindings in Textual's Binding format."""
    from textual.binding import Binding

    bindings = []
    for kb in KEYBINDINGS:
        # Only include single-key bindings for Textual
        # Command-style bindings (:w, :q, etc.) handled separately
        if not kb.key.startswith(":") and "/" not in kb.key and "-" not in kb.key:
            # Map special keys
            key = kb.key
            if key == "space":
                key = "space"
            elif key == "enter":
                key = "enter"
            elif key == "esc":
                key = "escape"

            # Create short description for footer
            desc = kb.description.split("(")[0].strip()[:20]
            bindings.append(Binding(key, kb.action, desc, show=False))

    return bindings
