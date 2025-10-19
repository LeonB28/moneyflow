"""
Amazon purchase data backend implementation.

Provides a read-only view of Amazon purchase history stored in SQLite.
This backend does not connect to any Amazon API - it works with locally
imported CSV files from Amazon's order history export.
"""

import hashlib
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import FinanceBackend


class AmazonBackend(FinanceBackend):
    """
    Amazon purchase history backend.

    This backend stores Amazon purchase data in a local SQLite database
    and provides a read-only view compatible with moneyflow's interface.

    Unlike Monarch, this backend doesn't connect to any API - data is
    imported from CSV files exported from Amazon.com.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the Amazon backend.

        Args:
            db_path: Path to SQLite database. Defaults to ~/.moneyflow/amazon.db

        Note: Database file is not created until first access (lazy initialization).
        """
        if db_path is None:
            db_path = str(Path.home() / ".moneyflow" / "amazon.db")

        self.db_path = Path(db_path).expanduser()
        self._db_initialized = False

    def _ensure_db_initialized(self) -> None:
        """Ensure database and schema are initialized on first access."""
        if self._db_initialized:
            return

        # Create directory if needed
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize schema
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                date TEXT NOT NULL,
                merchant TEXT NOT NULL,
                category TEXT,
                category_id TEXT,
                amount REAL NOT NULL,
                quantity INTEGER DEFAULT 1,
                price_per_item REAL,
                notes TEXT,
                hideFromReports INTEGER DEFAULT 0,
                imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS import_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                record_count INTEGER,
                duplicate_count INTEGER,
                import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes for performance
        conn.execute("CREATE INDEX IF NOT EXISTS idx_date ON transactions(date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_merchant ON transactions(merchant)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON transactions(category)")

        conn.commit()
        conn.close()

        self._db_initialized = True

    def _get_connection(self) -> sqlite3.Connection:
        """
        Get a database connection, initializing the database if needed.

        Returns:
            SQLite connection object
        """
        self._ensure_db_initialized()
        return sqlite3.connect(self.db_path)

    @staticmethod
    def generate_transaction_id(date: str, merchant: str, amount: float, quantity: int) -> str:
        """
        Generate a deterministic transaction ID for deduplication.

        Args:
            date: Transaction date (YYYY-MM-DD)
            merchant: Merchant/item name
            amount: Transaction amount
            quantity: Quantity purchased

        Returns:
            16-character hex string (first 16 chars of SHA256 hash)
        """
        fingerprint = f"{date}|{merchant}|{amount}|{quantity}"
        return hashlib.sha256(fingerprint.encode()).hexdigest()[:16]

    async def login(
        self,
        email: Optional[str] = None,
        password: Optional[str] = None,
        use_saved_session: bool = True,
        save_session: bool = True,
        mfa_secret_key: Optional[str] = None,
    ) -> None:
        """
        No-op login for Amazon backend.

        Amazon backend doesn't require authentication - it works with
        local data only.
        """
        # Amazon backend doesn't need login - data is local
        pass

    async def get_transactions(
        self,
        limit: int = 100,
        offset: int = 0,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Fetch transactions from local SQLite database.

        Args:
            limit: Maximum number of transactions to return
            offset: Number of transactions to skip (for pagination)
            start_date: Filter transactions from this date (ISO format: YYYY-MM-DD)
            end_date: Filter transactions to this date (ISO format: YYYY-MM-DD)

        Returns:
            Dictionary containing transaction data in Monarch-compatible format
        """
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row

        query = "SELECT * FROM transactions WHERE 1=1"
        params = []

        if start_date:
            query += " AND date >= ?"
            params.append(start_date)

        if end_date:
            query += " AND date <= ?"
            params.append(end_date)

        query += " ORDER BY date DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = conn.execute(query, params)
        rows = cursor.fetchall()

        # Get total count for pagination
        count_query = "SELECT COUNT(*) FROM transactions WHERE 1=1"
        count_params = []
        if start_date:
            count_query += " AND date >= ?"
            count_params.append(start_date)
        if end_date:
            count_query += " AND date <= ?"
            count_params.append(end_date)

        total_count = conn.execute(count_query, count_params).fetchone()[0]
        conn.close()

        # Convert to Monarch-compatible format
        transactions = []
        for row in rows:
            txn = {
                "id": row["id"],
                "date": row["date"],
                "amount": row["amount"],
                "merchant": {"id": row["merchant"], "name": row["merchant"]},
                "category": {
                    "id": row["category_id"] or row["category"] or "uncategorized",
                    "name": row["category"] or "Uncategorized",
                },
                "account": {"id": "amazon", "displayName": "Amazon"},  # Fake account
                "notes": row["notes"] or "",
                "hideFromReports": bool(row["hideFromReports"]),
                "pending": False,  # Amazon purchases are never pending
                "isRecurring": False,  # We don't track this for Amazon
                # Amazon-specific fields
                "quantity": row["quantity"],
                "price_per_item": row["price_per_item"],
            }
            transactions.append(txn)

        return {
            "allTransactions": transactions,
            "totalCount": total_count,
        }

    async def get_transaction_categories(self) -> Dict[str, Any]:
        """
        Fetch all categories from the database.

        Returns:
            Dictionary containing categories in Monarch-compatible format
        """
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row

        cursor = conn.execute("SELECT * FROM categories ORDER BY name")
        rows = cursor.fetchall()
        conn.close()

        categories = []
        for row in rows:
            categories.append(
                {
                    "id": row["id"],
                    "name": row["name"],
                    "group": None,  # Amazon doesn't use groups (yet)
                }
            )

        return {"categories": categories}

    async def get_transaction_category_groups(self) -> Dict[str, Any]:
        """
        Fetch category groups.

        Amazon backend doesn't support groups, returns empty list.
        """
        return {"categoryGroups": []}

    async def update_transaction(
        self,
        transaction_id: str,
        merchant_name: Optional[str] = None,
        category_id: Optional[str] = None,
        hide_from_reports: Optional[bool] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Update a transaction in the local database.

        Args:
            transaction_id: Unique identifier of the transaction
            merchant_name: New merchant/item name (if changing)
            category_id: New category ID (if changing)
            hide_from_reports: New hidden status (if changing)

        Returns:
            Dictionary containing the updated transaction data
        """
        conn = self._get_connection()

        updates = []
        params = []

        if merchant_name is not None:
            updates.append("merchant = ?")
            params.append(merchant_name)

        if category_id is not None:
            updates.append("category_id = ?")
            params.append(category_id)
            # Also update category name from categories table
            category_row = conn.execute(
                "SELECT name FROM categories WHERE id = ?", (category_id,)
            ).fetchone()
            if category_row:
                updates.append("category = ?")
                params.append(category_row[0])

        if hide_from_reports is not None:
            updates.append("hideFromReports = ?")
            params.append(1 if hide_from_reports else 0)

        if not updates:
            conn.close()
            return {"updateTransaction": {"transaction": {"id": transaction_id}}}

        params.append(transaction_id)
        query = f"UPDATE transactions SET {', '.join(updates)} WHERE id = ?"

        conn.execute(query, params)
        conn.commit()
        conn.close()

        return {"updateTransaction": {"transaction": {"id": transaction_id}}}

    async def delete_transaction(self, transaction_id: str) -> bool:
        """
        Delete a transaction from the database.

        Args:
            transaction_id: Unique identifier of the transaction

        Returns:
            True if deletion was successful
        """
        conn = self._get_connection()
        cursor = conn.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    async def get_all_merchants(self) -> List[str]:
        """
        Get all unique merchant/item names from the database.

        Returns:
            List of merchant names, sorted alphabetically
        """
        conn = self._get_connection()
        cursor = conn.execute("SELECT DISTINCT merchant FROM transactions ORDER BY merchant")
        merchants = [row[0] for row in cursor.fetchall()]
        conn.close()
        return merchants

    def get_import_history(self) -> List[Dict[str, Any]]:
        """
        Get history of CSV imports.

        Returns:
            List of import records with filename, counts, and timestamps
        """
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("""
            SELECT filename, record_count, duplicate_count, import_date
            FROM import_history
            ORDER BY import_date DESC
        """)
        history = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return history

    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the database.

        Returns:
            Dictionary with transaction count, date range, total amount, etc.
        """
        conn = self._get_connection()

        stats = {}

        # Total transactions
        stats["total_transactions"] = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[
            0
        ]

        # Date range
        date_range = conn.execute("""
            SELECT MIN(date) as min_date, MAX(date) as max_date
            FROM transactions
        """).fetchone()
        stats["earliest_date"] = date_range[0]
        stats["latest_date"] = date_range[1]

        # Total amount (remember, amounts are negative)
        total = conn.execute("SELECT SUM(amount) FROM transactions").fetchone()[0]
        stats["total_amount"] = total or 0.0

        # Category count
        stats["category_count"] = conn.execute(
            "SELECT COUNT(DISTINCT category) FROM transactions"
        ).fetchone()[0]

        # Item count
        stats["item_count"] = conn.execute(
            "SELECT COUNT(DISTINCT merchant) FROM transactions"
        ).fetchone()[0]

        conn.close()
        return stats
