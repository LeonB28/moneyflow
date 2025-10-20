"""
Edit screens for transaction modifications.

This module contains modal screens for editing transactions:
- EditMerchantScreen: Edit merchant names with autocomplete suggestions
- SelectCategoryScreen: Select category with type-to-search filtering
- DeleteConfirmationScreen: Confirm transaction deletion

All screens follow a consistent pattern:
1. Display transaction context (date, amount, current value)
2. Provide keyboard-driven input (type-to-search, arrow navigation)
3. Dismiss with new value or None (if cancelled)
"""

from textual.app import ComposeResult
from textual.containers import Container
from textual.events import Key
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, OptionList, Static
from textual.widgets.option_list import Option


class EditMerchantScreen(ModalScreen):
    """
    Modal screen for editing merchant names with autocomplete suggestions.

    Features:
    - Shows transaction context (date, amount, category)
    - Pre-fills current merchant name
    - Provides live-filtered suggestions from existing merchants
    - Supports both typing new name and selecting from list
    - Keyboard-driven: Enter=save, Esc=cancel, ↓=move to suggestions

    The screen handles both single and bulk edits:
    - Single edit: Shows transaction details
    - Bulk edit: Shows count and total amount

    Returns:
        str: New merchant name (if saved)
        None: If cancelled (Esc or Cancel button)
    """

    CSS = """
    EditMerchantScreen {
        align: center middle;
    }

    #edit-dialog {
        width: 70;
        height: auto;
        max-height: 40;
        border: thick $primary;
        background: $surface;
        padding: 2 4;
    }

    #edit-title {
        width: 100%;
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    .edit-label {
        margin-top: 1;
        color: $text;
    }

    .edit-input {
        margin-bottom: 1;
    }

    #suggestions {
        height: 15;
        border: solid $panel;
        margin: 1 0;
    }

    #suggestions-count {
        color: $text-muted;
        margin: 1 0;
    }

    #button-container {
        layout: horizontal;
        width: 100%;
        align: center middle;
        margin-top: 1;
    }

    #button-container Button {
        margin: 0 1;
    }
    """

    def __init__(
        self,
        current_merchant: str,
        transaction_count: int = 1,
        all_merchants: list = None,
        transaction_details: dict = None,
    ):
        super().__init__()
        self.current_merchant = current_merchant
        self.transaction_count = transaction_count
        self.all_merchants = all_merchants or []
        self.transaction_details = transaction_details

    def compose(self) -> ComposeResult:
        with Container(id="edit-dialog"):
            if self.transaction_count > 1:
                yield Label(
                    f"✏️  Edit Merchant ({self.transaction_count} transactions)", id="edit-title"
                )
            else:
                yield Label("✏️  Edit Merchant", id="edit-title")

            # Show transaction details or bulk edit summary
            if self.transaction_details:
                if self.transaction_count == 1:
                    # Single transaction details
                    amount = self.transaction_details.get('amount')
                    amount_str = f"${amount:,.2f}" if amount is not None else "N/A"
                    details_text = (
                        f"Transaction: {self.transaction_details.get('date', 'N/A')} | "
                        f"{amount_str} | "
                        f"{self.transaction_details.get('category', 'N/A')}"
                    )
                    yield Static(details_text, classes="edit-label")
                else:
                    # Bulk edit summary
                    total = self.transaction_details.get("total_amount", 0)
                    total_str = f"${total:,.2f}" if total is not None else "N/A"
                    details_text = (
                        f"Editing {self.transaction_count} transactions | Total: {total_str}"
                    )
                    yield Static(details_text, classes="edit-label")

            yield Label("Current merchant: " + self.current_merchant, classes="edit-label")

            yield Label("Type new name or ↓=Select from list below:", classes="edit-label")
            yield Input(
                placeholder="Type merchant name...",
                value=self.current_merchant,
                id="merchant-input",
                classes="edit-input",
            )

            if self.all_merchants:
                yield Static(
                    "Existing merchants - ↑/↓=Navigate | Enter=Select:", id="suggestions-count"
                )
                yield OptionList(id="suggestions")

            with Container(id="button-container"):
                yield Button("Save", variant="primary", id="save-button")
                yield Button("Cancel", variant="default", id="cancel-button")

    async def on_mount(self) -> None:
        """Initialize suggestions list."""
        if self.all_merchants:
            await self._update_suggestions("")
        self.query_one("#merchant-input", Input).focus()

    async def _update_suggestions(self, query: str) -> None:
        """Update merchant suggestions based on query."""
        option_list = self.query_one("#suggestions", OptionList)
        count_widget = self.query_one("#suggestions-count", Static)

        # Filter merchants
        if query and query != self.current_merchant.lower():
            matches = [
                m
                for m in self.all_merchants
                if m and query in m.lower() and m != self.current_merchant
            ]
        else:
            matches = [m for m in self.all_merchants if m and m != self.current_merchant]

        # Update count
        count_widget.update(f"{len(matches)} matching merchants - ↑/↓=Navigate | Enter=Select")

        # Clear and rebuild
        option_list.clear_options()

        # Show top 20 matches
        for merchant in sorted(set(matches))[:20]:
            option_list.add_option(Option(merchant, id=merchant))

        # Highlight first item by default so Enter works immediately
        if option_list.option_count > 0:
            option_list.highlighted = 0

    async def on_input_changed(self, event: Input.Changed) -> None:
        """Filter merchant suggestions as user types."""
        if event.input.id != "merchant-input" or not self.all_merchants:
            return

        query = event.value.lower().strip()
        await self._update_suggestions(query)

    async def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle merchant selection from suggestions."""
        if event.option.id:
            # Set input value and dismiss
            self.dismiss(str(event.option.id))

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-button":
            self.dismiss(None)
        elif event.button.id == "save-button":
            new_merchant = self.query_one("#merchant-input", Input).value.strip()
            if new_merchant and new_merchant != self.current_merchant:
                self.dismiss(new_merchant)
            else:
                self.dismiss(None)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in input - auto-select if only one match, else save typed value."""
        if event.input.id != "merchant-input":
            return

        # Check if there's exactly one filtered suggestion
        if self.all_merchants:
            option_list = self.query_one("#suggestions", OptionList)
            if option_list.option_count == 1:
                # Auto-select the single match
                highlighted_option = option_list.get_option_at_index(0)
                self.dismiss(str(highlighted_option.id))
                return

        # Otherwise save the typed value
        new_merchant = event.value.strip()
        if new_merchant and new_merchant != self.current_merchant:
            self.dismiss(new_merchant)
        else:
            self.dismiss(None)

    def on_key(self, event: Key) -> None:
        """Handle keyboard shortcuts."""
        if event.key == "escape":
            event.stop()  # Prevent propagation to parent
            self.dismiss(None)
        elif event.key == "down":
            # Move focus from input to suggestions (if list has items)
            if self.all_merchants:
                option_list = self.query_one("#suggestions", OptionList)
                if not option_list.has_focus and option_list.option_count > 0:
                    event.stop()  # Stop only when moving TO the list
                    option_list.focus()
        elif event.key == "up":
            # Move focus from list back to input (if at top of list)
            if self.all_merchants:
                option_list = self.query_one("#suggestions", OptionList)
                merchant_input = self.query_one("#merchant-input", Input)
                if option_list.has_focus and option_list.highlighted == 0:
                    event.stop()  # Stop to prevent default behavior
                    merchant_input.focus()


class SelectCategoryScreen(ModalScreen):
    """
    Modal screen for selecting transaction category with type-to-search.

    Features:
    - Shows transaction context (date, amount, merchant)
    - Live filtering as you type
    - Keyboard-driven list navigation (↑/↓ arrows, Enter to select)
    - Shows current category with "← current" indicator
    - Focus starts on search input for immediate typing

    The screen provides fast category selection for recategorization workflows.
    Type a few letters to filter hundreds of categories down to relevant matches.

    Returns:
        str: Selected category ID (if user selected a category)
        None: If cancelled (Esc key)

    Note: Lines 279-313 contain search/filter business logic that could be
    extracted to a CategorySearchService for better testability.
    See SECOND_PASS_ANALYSIS.md for details.
    """

    CSS = """
    SelectCategoryScreen {
        align: center middle;
    }

    #category-dialog {
        width: 70;
        height: auto;
        max-height: 35;
        border: thick $primary;
        background: $surface;
        padding: 2 4;
    }

    #category-title {
        width: 100%;
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    #search-input {
        margin: 1 0;
    }

    #category-list {
        height: 20;
        border: solid $panel;
        margin: 1 0;
    }

    #results-count {
        color: $text-muted;
        margin: 1 0;
    }
    """

    def __init__(
        self, categories: dict, current_category_id: str = None, transaction_details: dict = None
    ):
        super().__init__()
        self.categories = categories
        self.current_category_id = current_category_id
        self.category_map = {}  # Maps option index to category ID
        self.transaction_details = transaction_details

    def compose(self) -> ComposeResult:
        with Container(id="category-dialog"):
            yield Label(
                "📋 Select Category - Type to filter | ↑/↓=Navigate | Enter=Select",
                id="category-title",
            )

            # Show transaction details if available
            if self.transaction_details:
                amount = self.transaction_details.get('amount')
                amount_str = f"${amount:,.2f}" if amount is not None else "N/A"
                details_text = (
                    f"Transaction: {self.transaction_details.get('date', 'N/A')} | "
                    f"{amount_str} | "
                    f"Merchant: {self.transaction_details.get('merchant', 'N/A')}"
                )
                yield Static(details_text, classes="edit-label")

            # Show current category
            if self.current_category_id and self.current_category_id in self.categories:
                current_cat_name = self.categories[self.current_category_id]["name"]
                yield Label(f"Current category: {current_cat_name}", classes="edit-label")

            yield Input(placeholder="Type to filter categories...", id="search-input")

            yield Static(f"{len(self.categories)} categories", id="results-count")

            yield OptionList(id="category-list")

    async def on_mount(self) -> None:
        """Initialize category list."""
        await self._update_category_list("")
        # Focus search input so user can immediately start typing
        self.query_one("#search-input", Input).focus()

    async def _update_category_list(self, query: str) -> None:
        """Update the category list based on search query."""
        option_list = self.query_one("#category-list", OptionList)
        results_count = self.query_one("#results-count", Static)

        # Filter categories
        if query:
            matches = [
                (cat_id, cat_data)
                for cat_id, cat_data in self.categories.items()
                if query in cat_data["name"].lower()
            ]
        else:
            matches = list(self.categories.items())

        # Update count
        results_count.update(f"{len(matches)} categories")

        # Clear and rebuild list
        option_list.clear_options()
        self.category_map.clear()

        for idx, (cat_id, cat_data) in enumerate(sorted(matches, key=lambda x: x[1]["name"])):
            cat_name = cat_data["name"]
            is_current = " ← current" if cat_id == self.current_category_id else ""
            option_list.add_option(Option(f"{cat_name}{is_current}", id=cat_id))
            self.category_map[idx] = cat_id

        # Highlight first item by default so Enter works immediately
        if option_list.option_count > 0:
            option_list.highlighted = 0

    async def on_input_changed(self, event: Input.Changed) -> None:
        """Filter categories as user types."""
        if event.input.id != "search-input":
            return

        query = event.value.lower().strip()
        await self._update_category_list(query)

    async def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle category selection with Enter key."""
        if event.option.id:
            self.dismiss(str(event.option.id))

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in search - auto-select if only one match."""
        if event.input.id != "search-input":
            return

        option_list = self.query_one("#category-list", OptionList)
        if option_list.option_count == 1:
            # Auto-select the single match
            highlighted_option = option_list.get_option_at_index(0)
            self.dismiss(str(highlighted_option.id))
        elif option_list.option_count > 1 and option_list.highlighted is not None:
            # If there are multiple matches but one is highlighted, select it
            highlighted_option = option_list.get_option_at_index(option_list.highlighted)
            self.dismiss(str(highlighted_option.id))

    def on_key(self, event: Key) -> None:
        """Handle keyboard shortcuts."""
        if event.key == "escape":
            event.stop()  # Prevent propagation to parent
            self.dismiss(None)
        elif event.key == "down":
            # Move focus from search to list (if list has items)
            category_list = self.query_one("#category-list", OptionList)
            if not category_list.has_focus and category_list.option_count > 0:
                event.stop()  # Stop only when moving TO the list
                category_list.focus()
        elif event.key == "up":
            # Move focus from list back to search (if at top of list)
            category_list = self.query_one("#category-list", OptionList)
            search_input = self.query_one("#search-input", Input)
            if category_list.has_focus and category_list.highlighted == 0:
                event.stop()  # Stop to prevent default behavior
                search_input.focus()
        elif event.key == "slash":
            event.stop()  # Prevent propagation
            # Focus search input when user presses /
            self.query_one("#search-input", Input).focus()


class DeleteConfirmationScreen(ModalScreen):
    """Confirmation dialog for deleting transactions."""

    CSS = """
    DeleteConfirmationScreen {
        align: center middle;
    }

    #delete-dialog {
        width: 50;
        height: auto;
        border: thick $error;
        background: $surface;
        padding: 2 4;
    }

    #delete-title {
        width: 100%;
        text-align: center;
        text-style: bold;
        color: $error;
        margin-bottom: 1;
    }

    #delete-message {
        text-align: center;
        color: $text;
        margin-bottom: 2;
    }

    #button-container {
        layout: horizontal;
        width: 100%;
        align: center middle;
    }

    #button-container Button {
        margin: 0 1;
    }
    """

    def __init__(self, transaction_count: int = 1):
        super().__init__()
        self.transaction_count = transaction_count

    def compose(self) -> ComposeResult:
        with Container(id="delete-dialog"):
            yield Label("⚠️  Delete Transaction?", id="delete-title")

            if self.transaction_count > 1:
                yield Static(
                    f"Are you sure you want to delete {self.transaction_count} transactions?\n"
                    "This action CANNOT be undone!",
                    id="delete-message",
                )
            else:
                yield Static(
                    "Are you sure you want to delete this transaction?\n"
                    "This action CANNOT be undone!",
                    id="delete-message",
                )

            with Container(id="button-container"):
                yield Button("Cancel", variant="primary", id="cancel-button")
                yield Button("Delete", variant="error", id="delete-button")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-button":
            self.dismiss(False)
        elif event.button.id == "delete-button":
            self.dismiss(True)

    def on_key(self, event: Key) -> None:
        """Handle keyboard shortcuts."""
        if event.key == "escape":
            event.stop()  # Prevent propagation to parent
            self.dismiss(False)
