"""Tests for Amazon backend."""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from moneyflow.backends.amazon import AmazonBackend


@pytest.fixture
def temp_db():
    """Create a temporary database path for testing."""
    # Create a temp file to get a unique path, then delete it
    # Database will be created by lazy initialization
    with tempfile.NamedTemporaryFile(suffix=".db", delete=True) as f:
        db_path = f.name

    yield db_path

    # Cleanup (database might or might not exist)
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def backend(temp_db):
    """Create an AmazonBackend instance with temporary database."""
    return AmazonBackend(db_path=temp_db)


@pytest.fixture
def populated_backend(backend):
    """Create a backend with some test data."""
    # Trigger initialization
    conn = backend._get_connection()

    # Add test categories
    conn.execute("INSERT INTO categories (id, name) VALUES ('books', 'Books')")
    conn.execute("INSERT INTO categories (id, name) VALUES ('electronics', 'Electronics')")

    # Add test transactions
    conn.execute("""
        INSERT INTO transactions
        (id, date, merchant, category, category_id, amount, quantity, price_per_item, notes)
        VALUES
        ('txn1', '2024-01-15', 'Python Crash Course', 'Books', 'books', -39.99, 1, -39.99, 'Qty: 1'),
        ('txn2', '2024-01-20', 'USB-C Cable', 'Electronics', 'electronics', -15.99, 2, -7.995, 'Qty: 2'),
        ('txn3', '2024-02-10', 'Cooking for Engineers', 'Books', 'books', -29.99, 1, -29.99, 'Qty: 1')
    """)

    conn.commit()
    conn.close()

    return backend


class TestAmazonBackendInit:
    """Test backend initialization."""

    def test_init_creates_database(self, temp_db):
        """Test that database is created on first access (lazy initialization)."""
        backend = AmazonBackend(db_path=temp_db)
        # Database should NOT exist yet (lazy initialization)
        assert not Path(temp_db).exists()

        # Trigger initialization by accessing database
        backend._get_connection().close()

        # Now database should exist
        assert Path(temp_db).exists()

    def test_init_creates_tables(self, backend):
        """Test that initialization creates required tables."""
        conn = backend._get_connection()
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        assert "transactions" in tables
        assert "categories" in tables
        assert "import_history" in tables

    def test_init_creates_indexes(self, backend):
        """Test that initialization creates indexes."""
        conn = backend._get_connection()
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = {row[0] for row in cursor.fetchall()}
        conn.close()

        assert "idx_date" in indexes
        assert "idx_merchant" in indexes
        assert "idx_category" in indexes

    def test_default_db_path(self):
        """Test that default database path is ~/.moneyflow/amazon.db."""
        backend = AmazonBackend()
        expected_path = Path.home() / ".moneyflow" / "amazon.db"
        assert backend.db_path == expected_path


class TestTransactionIDGeneration:
    """Test transaction ID generation for deduplication."""

    def test_generate_id_deterministic(self):
        """Test that same inputs generate same ID."""
        id1 = AmazonBackend.generate_transaction_id("2024-01-15", "USB Cable", -15.99, 2)
        id2 = AmazonBackend.generate_transaction_id("2024-01-15", "USB Cable", -15.99, 2)
        assert id1 == id2

    def test_generate_id_different_date(self):
        """Test that different dates generate different IDs."""
        id1 = AmazonBackend.generate_transaction_id("2024-01-15", "USB Cable", -15.99, 2)
        id2 = AmazonBackend.generate_transaction_id("2024-01-16", "USB Cable", -15.99, 2)
        assert id1 != id2

    def test_generate_id_different_merchant(self):
        """Test that different merchants generate different IDs."""
        id1 = AmazonBackend.generate_transaction_id("2024-01-15", "USB Cable", -15.99, 2)
        id2 = AmazonBackend.generate_transaction_id("2024-01-15", "HDMI Cable", -15.99, 2)
        assert id1 != id2

    def test_generate_id_different_amount(self):
        """Test that different amounts generate different IDs."""
        id1 = AmazonBackend.generate_transaction_id("2024-01-15", "USB Cable", -15.99, 2)
        id2 = AmazonBackend.generate_transaction_id("2024-01-15", "USB Cable", -19.99, 2)
        assert id1 != id2

    def test_generate_id_different_quantity(self):
        """Test that different quantities generate different IDs."""
        id1 = AmazonBackend.generate_transaction_id("2024-01-15", "USB Cable", -15.99, 2)
        id2 = AmazonBackend.generate_transaction_id("2024-01-15", "USB Cable", -15.99, 3)
        assert id1 != id2

    def test_generate_id_length(self):
        """Test that generated ID is 16 characters."""
        txn_id = AmazonBackend.generate_transaction_id("2024-01-15", "USB Cable", -15.99, 2)
        assert len(txn_id) == 16


class TestGetTransactions:
    """Test fetching transactions."""

    @pytest.mark.asyncio
    async def test_get_transactions_empty(self, backend):
        """Test getting transactions from empty database."""
        result = await backend.get_transactions()
        assert result["allTransactions"] == []
        assert result["totalCount"] == 0

    @pytest.mark.asyncio
    async def test_get_transactions_basic(self, populated_backend):
        """Test getting all transactions."""
        result = await populated_backend.get_transactions(limit=100)

        assert len(result["allTransactions"]) == 3
        assert result["totalCount"] == 3

    @pytest.mark.asyncio
    async def test_get_transactions_limit(self, populated_backend):
        """Test limit parameter."""
        result = await populated_backend.get_transactions(limit=2)

        assert len(result["allTransactions"]) == 2
        assert result["totalCount"] == 3  # Total count unchanged

    @pytest.mark.asyncio
    async def test_get_transactions_offset(self, populated_backend):
        """Test offset parameter."""
        result = await populated_backend.get_transactions(limit=100, offset=1)

        assert len(result["allTransactions"]) == 2
        assert result["totalCount"] == 3

    @pytest.mark.asyncio
    async def test_get_transactions_date_filter(self, populated_backend):
        """Test filtering by date range."""
        result = await populated_backend.get_transactions(
            start_date="2024-01-20", end_date="2024-01-31"
        )

        assert len(result["allTransactions"]) == 1
        assert result["allTransactions"][0]["merchant"]["name"] == "USB-C Cable"

    @pytest.mark.asyncio
    async def test_get_transactions_format(self, populated_backend):
        """Test transaction format is Monarch-compatible."""
        result = await populated_backend.get_transactions(limit=1)
        txn = result["allTransactions"][0]

        # Check required fields
        assert "id" in txn
        assert "date" in txn
        assert "amount" in txn
        assert "merchant" in txn
        assert "category" in txn
        assert "account" in txn
        assert "notes" in txn
        assert "hideFromReports" in txn
        assert "pending" in txn
        assert "isRecurring" in txn

        # Check merchant format
        assert "id" in txn["merchant"]
        assert "name" in txn["merchant"]

        # Check category format
        assert "id" in txn["category"]
        assert "name" in txn["category"]

        # Check Amazon-specific fields
        assert "quantity" in txn
        assert "price_per_item" in txn

    @pytest.mark.asyncio
    async def test_get_transactions_order(self, populated_backend):
        """Test transactions are ordered by date descending."""
        result = await populated_backend.get_transactions()
        transactions = result["allTransactions"]

        # Should be ordered newest first
        assert transactions[0]["date"] == "2024-02-10"
        assert transactions[1]["date"] == "2024-01-20"
        assert transactions[2]["date"] == "2024-01-15"


class TestGetCategories:
    """Test fetching categories."""

    @pytest.mark.asyncio
    async def test_get_categories_empty(self, backend):
        """Test getting categories from empty database."""
        result = await backend.get_transaction_categories()
        assert result["categories"] == []

    @pytest.mark.asyncio
    async def test_get_categories(self, populated_backend):
        """Test getting categories."""
        result = await populated_backend.get_transaction_categories()

        assert len(result["categories"]) == 2

        # Check format
        category = result["categories"][0]
        assert "id" in category
        assert "name" in category
        assert "group" in category

    @pytest.mark.asyncio
    async def test_get_category_groups(self, backend):
        """Test getting category groups (should be empty for Amazon)."""
        result = await backend.get_transaction_category_groups()
        assert result["categoryGroups"] == []


class TestUpdateTransaction:
    """Test updating transactions."""

    @pytest.mark.asyncio
    async def test_update_merchant(self, populated_backend):
        """Test updating merchant name."""
        result = await populated_backend.update_transaction(
            transaction_id="txn1", merchant_name="Python Programming Book"
        )

        assert result["updateTransaction"]["transaction"]["id"] == "txn1"

        # Verify update
        conn = sqlite3.connect(populated_backend.db_path)
        row = conn.execute("SELECT merchant FROM transactions WHERE id = 'txn1'").fetchone()
        conn.close()

        assert row[0] == "Python Programming Book"

    @pytest.mark.asyncio
    async def test_update_category(self, populated_backend):
        """Test updating category."""
        result = await populated_backend.update_transaction(
            transaction_id="txn2", category_id="books"
        )

        assert result["updateTransaction"]["transaction"]["id"] == "txn2"

        # Verify update
        conn = sqlite3.connect(populated_backend.db_path)
        row = conn.execute(
            "SELECT category, category_id FROM transactions WHERE id = 'txn2'"
        ).fetchone()
        conn.close()

        assert row[0] == "Books"  # Category name updated from categories table
        assert row[1] == "books"

    @pytest.mark.asyncio
    async def test_update_hide_from_reports(self, populated_backend):
        """Test updating hideFromReports flag."""
        result = await populated_backend.update_transaction(
            transaction_id="txn1", hide_from_reports=True
        )

        assert result["updateTransaction"]["transaction"]["id"] == "txn1"

        # Verify update
        conn = sqlite3.connect(populated_backend.db_path)
        row = conn.execute("SELECT hideFromReports FROM transactions WHERE id = 'txn1'").fetchone()
        conn.close()

        assert row[0] == 1  # True stored as 1

    @pytest.mark.asyncio
    async def test_update_multiple_fields(self, populated_backend):
        """Test updating multiple fields at once."""
        result = await populated_backend.update_transaction(
            transaction_id="txn1",
            merchant_name="New Book Title",
            category_id="electronics",
            hide_from_reports=True,
        )

        assert result["updateTransaction"]["transaction"]["id"] == "txn1"

        # Verify all updates
        conn = sqlite3.connect(populated_backend.db_path)
        row = conn.execute(
            "SELECT merchant, category_id, hideFromReports FROM transactions WHERE id = 'txn1'"
        ).fetchone()
        conn.close()

        assert row[0] == "New Book Title"
        assert row[1] == "electronics"
        assert row[2] == 1


class TestDeleteTransaction:
    """Test deleting transactions."""

    @pytest.mark.asyncio
    async def test_delete_existing(self, populated_backend):
        """Test deleting an existing transaction."""
        result = await populated_backend.delete_transaction("txn1")

        assert result is True

        # Verify deletion
        conn = sqlite3.connect(populated_backend.db_path)
        count = conn.execute("SELECT COUNT(*) FROM transactions WHERE id = 'txn1'").fetchone()[0]
        conn.close()

        assert count == 0

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, populated_backend):
        """Test deleting a non-existent transaction."""
        result = await populated_backend.delete_transaction("nonexistent")

        assert result is False


class TestGetAllMerchants:
    """Test getting all merchants."""

    @pytest.mark.asyncio
    async def test_get_all_merchants_empty(self, backend):
        """Test getting merchants from empty database."""
        result = await backend.get_all_merchants()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_all_merchants(self, populated_backend):
        """Test getting all unique merchants."""
        result = await populated_backend.get_all_merchants()

        assert len(result) == 3
        assert "Python Crash Course" in result
        assert "USB-C Cable" in result
        assert "Cooking for Engineers" in result

    @pytest.mark.asyncio
    async def test_get_all_merchants_sorted(self, populated_backend):
        """Test that merchants are sorted alphabetically."""
        result = await populated_backend.get_all_merchants()

        assert result == sorted(result)


class TestDatabaseStats:
    """Test database statistics."""

    def test_get_stats_empty(self, backend):
        """Test stats for empty database."""
        stats = backend.get_database_stats()

        assert stats["total_transactions"] == 0
        assert stats["earliest_date"] is None
        assert stats["latest_date"] is None
        assert stats["total_amount"] == 0.0
        assert stats["category_count"] == 0
        assert stats["item_count"] == 0

    def test_get_stats_populated(self, populated_backend):
        """Test stats for populated database."""
        stats = populated_backend.get_database_stats()

        assert stats["total_transactions"] == 3
        assert stats["earliest_date"] == "2024-01-15"
        assert stats["latest_date"] == "2024-02-10"
        assert stats["total_amount"] == pytest.approx(-85.97)
        assert stats["category_count"] == 2
        assert stats["item_count"] == 3


class TestImportHistory:
    """Test import history tracking."""

    def test_get_import_history_empty(self, backend):
        """Test getting import history from empty database."""
        history = backend.get_import_history()
        assert history == []

    def test_get_import_history(self, backend):
        """Test getting import history."""
        # Add import records
        conn = backend._get_connection()
        conn.execute("""
            INSERT INTO import_history (filename, record_count, duplicate_count)
            VALUES ('purchases1.csv', 100, 5)
        """)
        conn.execute("""
            INSERT INTO import_history (filename, record_count, duplicate_count)
            VALUES ('purchases2.csv', 50, 10)
        """)
        conn.commit()
        conn.close()

        history = backend.get_import_history()

        assert len(history) == 2

        # Find each record (order may vary)
        filenames = {h["filename"] for h in history}
        assert "purchases1.csv" in filenames
        assert "purchases2.csv" in filenames

        # Check that records have correct data
        p2_record = next(h for h in history if h["filename"] == "purchases2.csv")
        assert p2_record["record_count"] == 50
        assert p2_record["duplicate_count"] == 10


class TestLogin:
    """Test login (should be no-op for Amazon)."""

    @pytest.mark.asyncio
    async def test_login_noop(self, backend):
        """Test that login does nothing for Amazon backend."""
        # Should not raise any exceptions
        await backend.login(email="test@example.com", password="test")
