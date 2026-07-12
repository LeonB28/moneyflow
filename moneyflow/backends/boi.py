from typing import Any, Dict, List, Optional
import polars as pl
from .base import FinanceBackend
import datetime
from pathlib import Path
import duckdb

from ..data.account_manager import AccountManager
import duckdb
import logging

logger = logging.getLogger(__name__)


class BankOfIreland(FinanceBackend):
    """
    Bank of Ireland purchase history backend.

    This backend stores Bank of Ireland purchase data in a local Duckdb database
    and provides a read-only view compatible with moneyflow's interface.

    Unlike cloud-based backends, this doesn't connect to any API - data is
    imported from transactions history as a CSV file using 365 online.
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        config_dir: str = str(Path.home() / ".moneyflow"),
    ):

        config_path = Path(config_dir)
        account_manager = AccountManager(config_dir=config_path)
        accounts = account_manager.list_accounts()

        # Look for an amazon account
        boi_account = None
        for account in accounts:
            if account.backend_type == "boi":
                boi_account = account
                break

        profile_dir = None
        if boi_account:
            # Use migrated profile path
            profile_dir = account_manager.get_profile_dir(boi_account.id)
            db_path = str(profile_dir / "boi.db")

        self.db_path = Path(db_path).expanduser()
        self.config_dir = config_dir
        self.profile_dir = profile_dir
        self._db_initialized = False
        self.categories_map = {}
        self.categories_group = []

    def get_connection(self) -> duckdb.DuckDBPyConnection:
        """Get a DuckDB connection."""
        self._ensure_db_initialized()
        return duckdb.connect(str(self.db_path))

    def _ensure_db_initialized(self) -> None:
        """Ensure database and schema are initialized on first access."""

        if self._db_initialized:
            return

        # Create directory if needed
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Connect to DuckDB (creates the file if it doesn't exist)
        with duckdb.connect(str(self.db_path)) as conn:
            # Create a sequence for the import ID if it doesn't exist
            conn.execute("CREATE SEQUENCE IF NOT EXISTS seq_transaction_id")

            # Create transactions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id VARCHAR PRIMARY KEY,
                    date DATE NOT NULL,
                    merchant VARCHAR NOT NULL,
                    debit DOUBLE,
                    credit DOUBLE
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS merchant (
                    merchant VARCHAR PRIMARY KEY,
                    display_name VARCHAR,
                    category_id VARCHAR,
                    category VARCHAR
                )
            """)

            # Create import history table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS import_history (
                    id INTEGER PRIMARY KEY DEFAULT nextval('seq_import_id'),
                    filename VARCHAR,
                    import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    record_count INTEGER
                )
            """)

        self._db_initialized = True

    async def login(
        self,
        email: Optional[str] = None,
        password: Optional[str] = None,
        use_saved_session: bool = True,
        save_session: bool = True,
        mfa_secret_key: Optional[str] = None,
    ) -> None:
        return

    async def get_transactions(
        self,
        limit: int = 100,
        offset: int = 0,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:

        if kwargs["hidden_from_reports"]:
            return {"allTransactions": {"results": [], "totalCount": 0}}

        with self.get_connection() as conn:
            query = f"""
                SELECT 
                    t.id as id,
                    t.date as date,
                    t.credit as credit,
                    t.debit as debit,
                    coalesce(m.display_name, t.merchant) as merchant,
                    coalesce(m.category, 'Uncategorized') as category,
                    coalesce(m.category_id, 'cat_uncategorized') as category_id,
                FROM transactions t
                LEFT JOIN merchant m on t.merchant = m.merchant 
                WHERE 1 = 1
            """
            if start_date:
                query += f" AND date >= '{start_date}'"

            if end_date:
                query += f" AND date <= '{end_date}'"

            query += f" LIMIT {limit} OFFSET {offset}"

            res = conn.execute(query).pl().to_dicts()
            # covert to list of dict of records
            results = [
                {
                    "id": row["id"],
                    "date": row["date"],
                    "amount": row["credit"] if row["credit"] else -1 * row["debit"],
                    "merchant": {"id": row["merchant"], "name": row["merchant"]},
                    "category": {"id": row["category_id"], "name": row["category"]},
                    "hideFromReports": False,
                    "pending": False,
                    "isRecurring": False,
                }
                for i, row in enumerate(res)
            ]
            return {"allTransactions": {"results": results, "totalCount": len(results)}}

    async def get_transaction_categories(self) -> Dict[str, Any]:
        """
        Fetch all categories for Bank of Ireland backend with smart inheritance.

        Priority order:
        1. Profile-local config.yaml (if exists)
        2. Built-in defaults

        Returns:
            Dictionary containing categories in standard format
        """
        categories = []
        cat_id_counter = 1

        category_groups = self._get_categories()
        # Build categories from loaded category groups
        for group_name, category_names in category_groups.items():
            for cat_name in category_names:
                cat_id = f"cat_{cat_name.lower().replace(' ', '_').replace('&', 'and')}"
                group_id = f"group_{group_name.lower().replace(' ', '_').replace('&', 'and')}"
                self.categories_map.update({cat_id: cat_name})
                self.categories_group.append(
                    {"id": group_id, "name": group_name, "type": "expense"}
                )
                categories.append(
                    {
                        "id": cat_id,
                        "name": cat_name,
                        "group": {"name": group_name, "id": group_name},
                    }
                )
                cat_id_counter += 1
        return {"categories": categories}

    async def get_transaction_category_groups(self) -> Dict[str, Any]:
        return {"categoryGroups": self.categories_group}

    async def update_transaction(
        self,
        transaction_id: str,
        merchant_name: Optional[str] = None,
        category_id: Optional[str] = None,
        hide_from_reports: Optional[bool] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        if not category_id and not merchant_name:
            return {"updateTransaction": {"transaction": {"id": transaction_id}}}

        if category_id:
            name = self.categories_map.get(category_id)
        else:
            name = "Uncategorized"
            category_id = "cat_uncategorized"
        if not merchant_name:
            values = f"""(SELECT merchant from transactions where id = '{transaction_id}'), null, '{name}', '{category_id}'"""
        else:
            values = f"""(SELECT merchant from transactions where id = '{transaction_id}'), '{merchant_name}', '{name}', '{category_id}'"""
        query = f"""
            INSERT into merchant (merchant, display_name, category, category_id)
            VALUES ({values})
            ON CONFLICT (merchant) DO UPDATE
            SET
        """
        if merchant_name:
            query += f"display_name = '{merchant_name}',"

        query += f" category_id = '{category_id}',"
        query += f" category = '{name}'"

        # query += f" WHERE merchant in (select merchant from transactions where id = '{transaction_id}')"

        with self.get_connection() as conn:
            conn.execute(query)
            return {"updateTransaction": {"transaction": {"id": transaction_id}}}

    async def delete_transaction(self, transaction_id: str) -> bool:
        pass

    def _get_categories(self):
        from moneyflow.data.categories import load_categories_from_profile

        if self.profile_dir:
            categories = load_categories_from_profile(self.profile_dir)
            if categories:
                return categories
        return {}

    def get_backend_type(self) -> str:
        return "boi"

    async def get_all_merchants(self) -> List[str]:
        query = """
            SELECT distinct coalesce(m.display_name, t.merchant) as merchant
            from transactions t join merchant m on t.merchant = m.merchant
            
        """
        with self.get_connection() as conn:
            res = conn.execute(query).pl().to_dicts()
            return [row["merchant"] for row in res]

    @property
    def supports_category_sync(self):
        return False
