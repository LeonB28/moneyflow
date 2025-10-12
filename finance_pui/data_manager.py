"""
Data management layer using Polars for high-performance aggregation and filtering.
"""

import asyncio
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Tuple
import polars as pl
from .backends.base import FinanceBackend


# Category group mapping (since not consistently available in API)
CATEGORY_GROUPS = {
    "Business": [
        "Office Rent",
        "Business Electronics",
        "Business Software",
    ],
    "Food & Dining": [
        "Restaurants & Bars",
        "Coffee Shops",
        "Groceries",
        "Fast Food",
        "Food & Drink",
        "Alcohol",
    ],
    "Travel": [
        "Airfare",
        "Hotel",
        "Trains",
        "Public Transit",
        "Taxi & Ride Shares",
        "Public Transit",
        "Luggage",
        "Travel Services",
    ],
    "Automotive": [
        "Gas",
        "Parking & Tolls",
        "Auto Payment",
        "Auto Maintenance",
    ],
    "Services": ["Internet & Cable", "Streaming"],
    "Housing": [
        "Gas & Electric",
        "Mortgage",
        "Rent",
        "Home Improvement",
        "Water",
        "Garbage",
        "Home Services",
    ],
    "Shopping": [
        "Shopping",
        "Clothing",
        "Electronics",
        "Kitchen",
        "Furniture & Housewares",
        "Jewelry & Accessories",
        "Video Games",
    ],
    "Entertainment": ["Entertainment & Recreation"],
    "Health & Fitness": [
        "Medical",
        "Dentist",
        "Fitness",
        "Pets",
        "Eyecare",
        "Supplements",
        "Workout Classes",
    ],
    "Personal": ["Personal", "Gifts", "Charity"],
    "Bills & Utilities": ["Phone", "Insurance"],
    "Financial": [
        "Financial & Legal Services",
        "Financial Fees",
        "Loan Repayment",
        "Student Loans",
    ],
    "Personal Care": ["Chiropractic & Massage", "Hair"],
    "Income": ["Paychecks", "Interest", "Business Income", "Other Income"],
    "Transfers": ["Transfer", "Credit Card Payment", "Balance Adjustments"],
    "Uncategorized": ["Uncategorized", "Check", "Miscellaneous"],
}


class DataManager:
    """
    Handles all data operations including fetching from API and
    local aggregations using Polars.
    """

    def __init__(self, mm: FinanceBackend):
        self.mm = mm
        self.category_to_group: Dict[str, str] = {}
        self._build_category_group_mapping()

        # Data storage
        self.df: Optional[pl.DataFrame] = None
        self.categories: Dict[str, Any] = {}
        self.category_groups: Dict[str, Any] = {}
        self.pending_edits: List[Any] = []

    def _build_category_group_mapping(self):
        """Build reverse mapping from category to group."""
        for group, categories in CATEGORY_GROUPS.items():
            for category in categories:
                self.category_to_group[category] = group

    async def fetch_all_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        progress_callback: Optional[callable] = None,
    ) -> Tuple[pl.DataFrame, Dict, Dict]:
        """
        Fetch all transactions and metadata from Monarch Money API.

        Returns:
            Tuple of (transactions_df, categories, category_groups)
        """
        # Fetch categories and groups in parallel
        if progress_callback:
            progress_callback("Fetching categories and groups...")

        categories_task = self.mm.get_transaction_categories()
        groups_task = self.mm.get_transaction_category_groups()

        categories_data, groups_data = await asyncio.gather(categories_task, groups_task)

        # Parse categories
        categories = {}
        for cat in categories_data.get("categories", []):
            categories[cat["id"]] = {
                "name": cat["name"],
                "group_id": cat.get("group", {}).get("id"),
                "group_type": cat.get("group", {}).get("type"),
            }

        # Parse category groups
        category_groups = {}
        for group in groups_data.get("categoryGroups", []):
            category_groups[group["id"]] = {
                "name": group["name"],
                "type": group["type"],
            }

        # Fetch transactions in batches
        if progress_callback:
            progress_callback("Fetching transactions...")

        transactions = await self._fetch_all_transactions(
            start_date=start_date, end_date=end_date, progress_callback=progress_callback
        )

        # Convert to Polars DataFrame
        if progress_callback:
            progress_callback("Processing transactions...")

        df = self._transactions_to_dataframe(transactions, categories)

        # Apply category grouping (done dynamically so CATEGORY_GROUPS changes take effect)
        df = self.apply_category_groups(df)

        return df, categories, category_groups

    async def _fetch_all_transactions(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        progress_callback: Optional[callable] = None,
    ) -> List[Dict]:
        """Fetch all transactions from API in batches."""
        all_transactions = []
        batch_size = 1000
        offset = 0
        batch_num = 1
        total_count = None

        while True:
            batch = await self.mm.get_transactions(
                start_date=start_date, end_date=end_date, limit=batch_size, offset=offset
            )

            # Get total count on first batch
            if total_count is None and "allTransactions" in batch:
                total_count = batch["allTransactions"].get("totalCount", 0)
                if progress_callback and total_count:
                    progress_callback(
                        f"Found {total_count:,} total transactions. Starting download..."
                    )

            # Get results from batch
            batch_results = []
            if "allTransactions" in batch:
                batch_results = batch["allTransactions"].get("results", [])
            elif "results" in batch:
                batch_results = batch["results"]

            if not batch_results:
                break

            all_transactions.extend(batch_results)

            # Show progress
            if progress_callback:
                if total_count:
                    pct = int((len(all_transactions) / total_count) * 100)
                    progress_callback(
                        f"Downloaded {len(all_transactions):,} / {total_count:,} transactions ({pct}%)"
                    )
                else:
                    progress_callback(f"Downloaded {len(all_transactions):,} transactions...")

            offset += batch_size
            batch_num += 1

            # Break if we got fewer results than batch size
            if len(batch_results) < batch_size:
                break

        if progress_callback:
            progress_callback(f"✓ Downloaded {len(all_transactions):,} transactions")

        return all_transactions

    def _transactions_to_dataframe(
        self, transactions: List[Dict], categories: Dict
    ) -> pl.DataFrame:
        """
        Convert raw transaction data to Polars DataFrame with enriched fields.

        Note: Does NOT include 'group' field - groups are applied dynamically
        via apply_category_groups() so changes to CATEGORY_GROUPS take effect
        on cached data.
        """
        if not transactions:
            return pl.DataFrame()

        # Prepare data for DataFrame
        rows = []
        for txn in transactions:
            merchant_obj = txn.get("merchant", {}) or {}
            category_obj = txn.get("category", {}) or {}
            account_obj = txn.get("account", {}) or {}

            category_id = category_obj.get("id", "")
            category_name = category_obj.get("name", "Uncategorized")

            row = {
                "id": str(txn.get("id", "")),
                "date": str(txn.get("date", "")),
                "amount": float(txn.get("amount", 0)),
                "merchant": str(
                    merchant_obj.get("name", "") if merchant_obj.get("name") else "Unknown"
                ),
                "merchant_id": str(merchant_obj.get("id", "")),
                "category": str(category_name if category_name else "Uncategorized"),
                "category_id": str(category_id),
                # Note: 'group' field NOT included here - added dynamically
                "account": str(
                    account_obj.get("displayName", "") if account_obj.get("displayName") else ""
                ),
                "account_id": str(account_obj.get("id", "")),
                "notes": str(txn.get("notes", "") if txn.get("notes") else ""),
                "hideFromReports": bool(txn.get("hideFromReports", False)),
                "pending": bool(txn.get("pending", False)),
                "isRecurring": bool(txn.get("isRecurring", False)),
            }
            rows.append(row)

        # Create DataFrame
        df = pl.DataFrame(rows)

        # Convert date column to date type
        df = df.with_columns(pl.col("date").str.strptime(pl.Date, format="%Y-%m-%d"))

        return df

    def apply_category_groups(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Apply category-to-group mapping to a DataFrame.

        This adds/updates the 'group' column based on CATEGORY_GROUPS mapping.
        Called after loading data (from API or cache) so that changes to
        CATEGORY_GROUPS always take effect.

        Args:
            df: DataFrame with 'category' column

        Returns:
            DataFrame with 'group' column added/updated
        """
        if df.is_empty():
            return df

        # Create a mapping expression for Polars
        # For each category, map to its group (or "Uncategorized" if not mapped)
        def get_group(category: str) -> str:
            return self.category_to_group.get(category, "Uncategorized")

        # Apply mapping - use Polars map_elements for efficient lookup
        df = df.with_columns(
            pl.col("category").map_elements(get_group, return_dtype=pl.String).alias("group")
        )

        return df

    def aggregate_by_merchant(self, df: pl.DataFrame) -> pl.DataFrame:
        """Aggregate transactions by merchant."""
        if df.is_empty():
            return pl.DataFrame()

        return df.group_by("merchant").agg(
            [
                pl.count("id").alias("count"),
                pl.sum("amount").alias("total"),
                pl.first("merchant_id").alias("merchant_id"),
            ]
        )

    def aggregate_by_category(self, df: pl.DataFrame) -> pl.DataFrame:
        """Aggregate transactions by category."""
        if df.is_empty():
            return pl.DataFrame()

        return df.group_by("category").agg(
            [
                pl.count("id").alias("count"),
                pl.sum("amount").alias("total"),
                pl.first("category_id").alias("category_id"),
                pl.first("group").alias("group"),
            ]
        )

    def aggregate_by_group(self, df: pl.DataFrame) -> pl.DataFrame:
        """Aggregate transactions by category group."""
        if df.is_empty():
            return pl.DataFrame()

        return df.group_by("group").agg(
            [
                pl.count("id").alias("count"),
                pl.sum("amount").alias("total"),
            ]
        )

    def aggregate_by_account(self, df: pl.DataFrame) -> pl.DataFrame:
        """Aggregate transactions by account."""
        if df.is_empty():
            return pl.DataFrame()

        return df.group_by("account").agg(
            [
                pl.count("id").alias("count"),
                pl.sum("amount").alias("total"),
                pl.first("account_id").alias("account_id"),
            ]
        )

    def filter_by_merchant(self, df: pl.DataFrame, merchant: str) -> pl.DataFrame:
        """Filter transactions by merchant name."""
        return df.filter(pl.col("merchant") == merchant)

    def filter_by_category(self, df: pl.DataFrame, category: str) -> pl.DataFrame:
        """Filter transactions by category name."""
        return df.filter(pl.col("category") == category)

    def filter_by_group(self, df: pl.DataFrame, group: str) -> pl.DataFrame:
        """Filter transactions by group name."""
        return df.filter(pl.col("group") == group)

    def filter_by_account(self, df: pl.DataFrame, account: str) -> pl.DataFrame:
        """Filter transactions by account name."""
        return df.filter(pl.col("account") == account)

    def search_transactions(self, df: pl.DataFrame, query: str) -> pl.DataFrame:
        """Search transactions by merchant, category, or notes."""
        if not query:
            return df

        query_lower = query.lower()
        return df.filter(
            pl.col("merchant").str.to_lowercase().str.contains(query_lower)
            | pl.col("category").str.to_lowercase().str.contains(query_lower)
            | pl.col("notes").str.to_lowercase().str.contains(query_lower)
        )

    async def commit_pending_edits(self, edits: List[Any]) -> Tuple[int, int]:
        """
        Commit pending edits to Monarch Money API in parallel.

        Returns:
            Tuple of (success_count, failure_count)
        """
        if not edits:
            return 0, 0

        # Group edits by transaction ID
        edits_by_txn: Dict[str, Dict[str, Any]] = {}
        for edit in edits:
            txn_id = edit.transaction_id
            if txn_id not in edits_by_txn:
                edits_by_txn[txn_id] = {}

            if edit.field == "merchant":
                edits_by_txn[txn_id]["merchant_name"] = edit.new_value
            elif edit.field == "category":
                edits_by_txn[txn_id]["category_id"] = edit.new_value
            elif edit.field == "hide_from_reports":
                edits_by_txn[txn_id]["hide_from_reports"] = edit.new_value

        # Create update tasks
        tasks = []
        for txn_id, updates in edits_by_txn.items():
            tasks.append(self.mm.update_transaction(transaction_id=txn_id, **updates))

        # Execute in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successes and failures
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        failure_count = len(results) - success_count

        return success_count, failure_count

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about current data."""
        if self.df is None or self.df.is_empty():
            return {
                "total_transactions": 0,
                "total_amount": 0.0,
                "pending_changes": len(self.pending_edits),
            }

        return {
            "total_transactions": len(self.df),
            "total_amount": float(self.df["amount"].sum()),
            "pending_changes": len(self.pending_edits),
        }
