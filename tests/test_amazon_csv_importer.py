"""Tests for Amazon CSV importer."""

import asyncio
import tempfile
from pathlib import Path

import pytest

from moneyflow.backends.amazon import AmazonBackend
from moneyflow.importers.amazon_csv import (
    get_category_statistics,
    import_amazon_csv,
    normalize_category,
)


def run_async(coro):
    """Helper to run async functions synchronously in tests."""
    return asyncio.run(coro)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    yield db_path

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def backend(temp_db):
    """Create an AmazonBackend instance with temporary database."""
    return AmazonBackend(db_path=temp_db)


@pytest.fixture
def sample_csv():
    """Create a sample CSV file for testing."""
    csv_content = """Order Date,Title,Category,Quantity,Item Total,Reimbursed,Year,Regret,Disposed,Sale Price
01/15/2024,Python Crash Course,Books,1,39.99,,,,,
01/20/2024,USB-C Cable,Electronics,2,15.99,,,,,
02/10/2024,Cooking for Engineers,Books,1,29.99,,,,,
02/15/2024,HDMI Cable,Electronics,1,12.99,,,,,
03/01/2024,Coffee Maker,Kitchen,1,89.99,,,,,
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(csv_content)
        csv_path = f.name

    yield csv_path

    # Cleanup
    Path(csv_path).unlink(missing_ok=True)


@pytest.fixture
def csv_with_variations():
    """Create CSV with category variations for normalization testing."""
    csv_content = """Order Date,Title,Category,Quantity,Item Total
01/15/2024,Book 1,Books,1,19.99
01/16/2024,Book 2,BOoks,1,29.99
01/17/2024,Game 1,Video Game,1,59.99
01/18/2024,Game 2,VIdeo Game,1,49.99
01/19/2024,Office Stuff,Office Product,1,9.99
01/20/2024,More Office Stuff,Office Products,1,14.99
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(csv_content)
        csv_path = f.name

    yield csv_path

    # Cleanup
    Path(csv_path).unlink(missing_ok=True)


class TestCategoryNormalization:
    """Test category normalization."""

    def test_normalize_books_variant(self):
        """Test normalizing BOoks to Books."""
        assert normalize_category("BOoks") == "Books"

    def test_normalize_video_game_variant(self):
        """Test normalizing VIdeo Game to Video Game."""
        assert normalize_category("VIdeo Game") == "Video Game"

    def test_normalize_office_products(self):
        """Test normalizing Office Products to Office Product."""
        assert normalize_category("Office Products") == "Office Product"

    def test_normalize_unchanged(self):
        """Test that normal categories are unchanged."""
        assert normalize_category("Books") == "Books"
        assert normalize_category("Electronics") == "Electronics"
        assert normalize_category("Kitchen") == "Kitchen"


class TestImportBasic:
    """Test basic CSV import functionality."""

    def test_import_sample_csv(self, sample_csv, backend):
        """Test importing a sample CSV file."""
        stats = import_amazon_csv(sample_csv, backend=backend)

        assert stats["total_rows"] == 5
        assert stats["imported"] == 5
        assert stats["duplicates"] == 0
        assert stats["categories_created"] == 3  # Books, Electronics, Kitchen

    def test_import_creates_categories(self, sample_csv, backend):
        """Test that import creates category records."""
        import_amazon_csv(sample_csv, backend=backend)

        result = run_async(backend.get_transaction_categories())
        categories = {cat["name"] for cat in result["categories"]}

        assert "Books" in categories
        assert "Electronics" in categories
        assert "Kitchen" in categories

    def test_import_creates_transactions(self, sample_csv, backend):
        """Test that import creates transaction records."""
        import_amazon_csv(sample_csv, backend=backend)

        result = run_async(backend.get_transactions(limit=100))
        transactions = result["allTransactions"]

        assert len(transactions) == 5

        # Check first transaction
        txn = transactions[-1]  # Last in list (oldest date)
        assert txn["date"] == "2024-01-15"
        assert txn["merchant"]["name"] == "Python Crash Course"
        assert txn["category"]["name"] == "Books"
        assert txn["amount"] == -39.99  # Should be negative
        assert txn["quantity"] == 1
        assert txn["price_per_item"] == -39.99

    def test_import_flips_sign(self, sample_csv, backend):
        """Test that positive amounts in CSV become negative."""
        import_amazon_csv(sample_csv, backend=backend)

        result = run_async(backend.get_transactions(limit=100))

        # All amounts should be negative (expenses)
        for txn in result["allTransactions"]:
            assert txn["amount"] < 0

    def test_import_calculates_price_per_item(self, sample_csv, backend):
        """Test that price per item is calculated correctly."""
        import_amazon_csv(sample_csv, backend=backend)

        result = run_async(backend.get_transactions())

        # Find the USB-C Cable transaction (qty 2)
        usb_cable = next(
            txn for txn in result["allTransactions"] if txn["merchant"]["name"] == "USB-C Cable"
        )

        assert usb_cable["quantity"] == 2
        assert usb_cable["amount"] == -15.99
        assert usb_cable["price_per_item"] == pytest.approx(-7.995)


class TestImportDuplicateHandling:
    """Test duplicate detection and handling."""

    def test_import_twice_skips_duplicates(self, sample_csv, backend):
        """Test that importing same file twice skips duplicates."""
        # First import
        stats1 = import_amazon_csv(sample_csv, backend=backend)
        assert stats1["imported"] == 5
        assert stats1["duplicates"] == 0

        # Second import
        stats2 = import_amazon_csv(sample_csv, backend=backend)
        assert stats2["imported"] == 0
        assert stats2["duplicates"] == 5

        # Verify only 5 transactions in database
        result = run_async(backend.get_transactions(limit=100))
        assert len(result["allTransactions"]) == 5

    def test_import_force_overwrites_duplicates(self, sample_csv, backend):
        """Test that force=True overwrites existing transactions."""
        # First import
        import_amazon_csv(sample_csv, backend=backend)

        # Second import with force
        stats = import_amazon_csv(sample_csv, backend=backend, force=True)

        assert stats["imported"] == 0
        assert stats["duplicates"] == 5

        # Verify still only 5 transactions
        result = run_async(backend.get_transactions(limit=100))
        assert len(result["allTransactions"]) == 5


class TestImportCategoryNormalization:
    """Test category normalization during import."""

    def test_import_normalizes_categories(self, csv_with_variations, backend):
        """Test that categories are normalized during import."""
        import_amazon_csv(csv_with_variations, backend=backend)

        result = run_async(backend.get_transaction_categories())
        category_names = {cat["name"] for cat in result["categories"]}

        # Should have normalized names only
        assert "Books" in category_names
        assert "BOoks" not in category_names

        assert "Video Game" in category_names
        assert "VIdeo Game" not in category_names

        assert "Office Product" in category_names
        # Note: Both "Office Product" and "Office Products" might be present
        # since we only normalize "Office Products" -> "Office Product"

    def test_import_consolidates_transactions(self, csv_with_variations, backend):
        """Test that transactions with variant categories are consolidated."""
        import_amazon_csv(csv_with_variations, backend=backend)

        result = run_async(backend.get_transactions(limit=100))

        # All book transactions should have "Books" category
        book_txns = [txn for txn in result["allTransactions"] if "Book" in txn["merchant"]["name"]]
        assert len(book_txns) == 2
        for txn in book_txns:
            assert txn["category"]["name"] == "Books"


class TestImportHistory:
    """Test import history tracking."""

    def test_import_records_history(self, sample_csv, backend):
        """Test that import is recorded in history."""
        import_amazon_csv(sample_csv, backend=backend)

        history = backend.get_import_history()

        assert len(history) == 1
        assert (
            "purchases" in history[0]["filename"].lower() or "tmp" in history[0]["filename"].lower()
        )
        assert history[0]["record_count"] == 5
        assert history[0]["duplicate_count"] == 0

    def test_import_history_tracks_duplicates(self, sample_csv, backend):
        """Test that duplicate count is tracked in history."""
        # First import
        import_amazon_csv(sample_csv, backend=backend)

        # Second import
        import_amazon_csv(sample_csv, backend=backend)

        history = backend.get_import_history()

        assert len(history) == 2

        # Find the record with duplicates (should be the second import)
        duplicate_counts = [h["duplicate_count"] for h in history]
        assert 5 in duplicate_counts  # Second import should have 5 duplicates
        assert 0 in duplicate_counts  # First import should have 0 duplicates


class TestImportValidation:
    """Test CSV validation."""

    def test_import_missing_columns(self, backend):
        """Test that import fails with missing required columns."""
        csv_content = """Date,Item,Price
01/15/2024,Book,19.99
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            csv_path = f.name

        try:
            with pytest.raises(ValueError, match="Missing required columns"):
                import_amazon_csv(csv_path, backend=backend)
        finally:
            Path(csv_path).unlink()

    def test_import_filters_invalid_quantity(self, backend):
        """Test that rows with quantity <= 0 are filtered out."""
        csv_content = """Order Date,Title,Category,Quantity,Item Total
01/15/2024,Valid Item,Books,1,19.99
01/16/2024,Invalid Item,Books,0,29.99
01/17/2024,Another Invalid,Books,-1,39.99
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            csv_path = f.name

        try:
            stats = import_amazon_csv(csv_path, backend=backend)

            # Only 1 valid row should be imported
            assert stats["total_rows"] == 1  # After filtering
            assert stats["imported"] == 1

            result = run_async(backend.get_transactions())
            assert len(result["allTransactions"]) == 1
            assert result["allTransactions"][0]["merchant"]["name"] == "Valid Item"
        finally:
            Path(csv_path).unlink()


class TestCategoryStatistics:
    """Test category statistics."""

    def test_get_category_statistics(self, sample_csv, backend):
        """Test getting spending statistics by category."""
        import_amazon_csv(sample_csv, backend=backend)

        stats = get_category_statistics(backend=backend)

        # Should have stats for all categories
        assert "Books" in stats
        assert "Electronics" in stats
        assert "Kitchen" in stats

        # Check Books category (2 items: $39.99 + $29.99 = $69.98)
        books_count, books_total = stats["Books"]
        assert books_count == 2
        assert books_total == pytest.approx(-69.98)

        # Check Electronics category (2 items: $15.99 + $12.99 = $28.98)
        electronics_count, electronics_total = stats["Electronics"]
        assert electronics_count == 2
        assert electronics_total == pytest.approx(-28.98)

        # Check Kitchen category (1 item: $89.99)
        kitchen_count, kitchen_total = stats["Kitchen"]
        assert kitchen_count == 1
        assert kitchen_total == pytest.approx(-89.99)


class TestImportEdgeCases:
    """Test edge cases in import."""

    def test_import_null_category(self, backend):
        """Test that null categories are filled with 'Misc.'."""
        csv_content = """Order Date,Title,Category,Quantity,Item Total
01/15/2024,Mystery Item,,1,19.99
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            csv_path = f.name

        try:
            import_amazon_csv(csv_path, backend=backend)

            result = run_async(backend.get_transactions())
            txn = result["allTransactions"][0]

            assert txn["category"]["name"] == "Misc."
        finally:
            Path(csv_path).unlink()

    def test_import_unicode_characters(self, backend):
        """Test importing items with unicode characters."""
        csv_content = """Order Date,Title,Category,Quantity,Item Total
01/15/2024,Caf� Bustelo Coffee,Grocery,1,8.99
01/16/2024,Se�or Rio Salsa,Grocery,1,4.99
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            f.write(csv_content)
            csv_path = f.name

        try:
            stats = import_amazon_csv(csv_path, backend=backend)

            assert stats["imported"] == 2

            result = run_async(backend.get_transactions())
            merchants = {txn["merchant"]["name"] for txn in result["allTransactions"]}

            assert "Caf� Bustelo Coffee" in merchants
            assert "Se�or Rio Salsa" in merchants
        finally:
            Path(csv_path).unlink()

    def test_import_special_characters(self, backend):
        """Test importing items with special characters."""
        # Using raw string to avoid parsing issues
        lines = [
            "Order Date,Title,Category,Quantity,Item Total",
            '01/15/2024,"Item with ""quotes""",Books,1,19.99',
            "01/16/2024,Item with & ampersand,Books,1,29.99",
        ]
        csv_content = "\n".join(lines) + "\n"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            csv_path = f.name

        try:
            stats = import_amazon_csv(csv_path, backend=backend)

            assert stats["imported"] == 2
        finally:
            Path(csv_path).unlink()
