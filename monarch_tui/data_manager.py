"""
Data management layer using Polars for high-performance aggregations.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import polars as pl

from .monarchmoney import MonarchMoney


class DataManager:
    """
    Manages transaction data with fast aggregations using Polars.

    Responsibilities:
    - Fetch all transactions from Monarch API
    - Maintain in-memory Polars DataFrame for fast filtering/aggregation
    - Track pending changes before committing
    - Provide aggregation views (by merchant, category, group)
    """

    def __init__(self, mm: MonarchMoney):
        self.mm = mm
        self.df: Optional[pl.DataFrame] = None
        self.categories: Dict[str, Any] = {}
        self.category_groups: Dict[str, Any] = {}
        self.merchants: Dict[str, Any] = {}

        # Pending changes (undo/redo support)
        self.pending_changes: List[Dict] = []
        self.change_history: List[Dict] = []
        self.change_index: int = -1

        # Category group mapping (custom or from API)
        self.group_mapping: Dict[str, str] = self._default_group_mapping()

    def _default_group_mapping(self) -> Dict[str, str]:
        """Default category to group mapping."""
        return {
            # Food & Dining
            "Restaurants & Bars": "Food & Dining",
            "Coffee Shops": "Food & Dining",
            "Groceries": "Food & Dining",
            "Food & Drink": "Food & Dining",

            # Transportation
            "Gas": "Transportation",
            "Public Transit": "Transportation",
            "Parking & Tolls": "Transportation",
            "Taxi & Ride Shares": "Transportation",
            "Auto Maintenance": "Transportation",
            "Auto Payment": "Transportation",

            # Home
            "Mortgage": "Home",
            "Rent": "Home",
            "Home Improvement": "Home",
            "Utilities": "Home",
            "Gas & Electric": "Home",
            "Water": "Home",
            "Garbage": "Home",
            "Internet & Cable": "Home",
            "Phone": "Home",
            "Furniture & Housewares": "Home",

            # Shopping
            "Shopping": "Shopping",
            "Clothing": "Shopping",
            "Electronics": "Shopping",

            # Travel
            "Travel & Vacation": "Travel",

            # Health & Fitness
            "Medical": "Health & Fitness",
            "Dentist": "Health & Fitness",
            "Fitness": "Health & Fitness",
            "Pharmacy": "Health & Fitness",

            # Entertainment
            "Entertainment & Recreation": "Entertainment",
            "Fun Money": "Entertainment",

            # Personal
            "Personal": "Personal",
            "Pets": "Personal",
            "Gifts": "Personal",
            "Charity": "Personal",

            # Financial
            "Financial & Legal Services": "Financial",
            "Financial Fees": "Financial",
            "Insurance": "Financial",
            "Taxes": "Financial",
            "Loan Repayment": "Financial",
            "Student Loans": "Financial",

            # Income
            "Paychecks": "Income",
            "Interest": "Income",
            "Business Income": "Income",
            "Other Income": "Income",

            # Transfers
            "Transfer": "Transfers",
            "Credit Card Payment": "Transfers",
            "Balance Adjustments": "Transfers",
        }

    async def load_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        progress_callback=None
    ) -> None:
        """
        Load all transaction data from Monarch API.

        Args:
            start_date: ISO date string (YYYY-MM-DD) or None for default
            end_date: ISO date string (YYYY-MM-DD) or None for default
            progress_callback: Optional callback(current, total, status_msg)
        """
        # Default to last year if not specified
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')

        # Fetch metadata first
        if progress_callback:
            progress_callback(0, 3, "Loading categories...")

        categories_data = await self.mm.get_transaction_categories()
        self.categories = {
            cat['id']: cat for cat in categories_data.get('categories', [])
        }

        if progress_callback:
            progress_callback(1, 3, "Loading category groups...")

        groups_data = await self.mm.get_transaction_category_groups()
        self.category_groups = {
            grp['id']: grp for grp in groups_data.get('categoryGroups', [])
        }

        # Fetch transactions in batches
        if progress_callback:
            progress_callback(2, 3, "Loading transactions...")

        all_transactions = []
        batch_size = 1000
        offset = 0

        while True:
            batch = await self.mm.get_transactions(
                start_date=start_date,
                end_date=end_date,
                limit=batch_size,
                offset=offset
            )

            batch_results = batch.get('allTransactions', {}).get('results', [])
            if not batch_results:
                break

            all_transactions.extend(batch_results)

            if progress_callback:
                progress_callback(
                    2, 3,
                    f"Loaded {len(all_transactions)} transactions..."
                )

            if len(batch_results) < batch_size:
                break

            offset += batch_size

        # Convert to Polars DataFrame
        self._build_dataframe(all_transactions)

        if progress_callback:
            progress_callback(3, 3, f"Loaded {len(all_transactions)} transactions!")

    def _build_dataframe(self, transactions: List[Dict]) -> None:
        """Build Polars DataFrame from transaction data."""
        # Flatten transaction structure
        records = []
        for txn in transactions:
            merchant = txn.get('merchant') or {}
            category = txn.get('category') or {}
            account = txn.get('account') or {}

            category_name = category.get('name', 'Uncategorized')
            group_name = self.group_mapping.get(category_name, 'Other')

            records.append({
                'id': txn['id'],
                'date': txn['date'],
                'amount': float(txn['amount']),
                'merchant_id': merchant.get('id'),
                'merchant': merchant.get('name', 'Unknown'),
                'category_id': category.get('id'),
                'category': category_name,
                'group': group_name,
                'account_id': account.get('id'),
                'account': account.get('displayName', 'Unknown'),
                'notes': txn.get('notes', ''),
                'hideFromReports': txn.get('hideFromReports', False),
                'pending': txn.get('pending', False),
                'isRecurring': txn.get('isRecurring', False),
            })

        self.df = pl.DataFrame(records)

    def aggregate_by_merchant(self, sort_by: str = "count") -> pl.DataFrame:
        """
        Aggregate transactions by merchant.

        Args:
            sort_by: 'count', 'total', or 'merchant'

        Returns:
            Polars DataFrame with merchant aggregations
        """
        if self.df is None or len(self.df) == 0:
            return pl.DataFrame()

        agg = self.df.group_by('merchant').agg([
            pl.count('id').alias('count'),
            pl.sum('amount').alias('total'),
            pl.first('merchant_id').alias('merchant_id'),
        ])

        # Sort
        if sort_by == "count":
            agg = agg.sort('count', descending=True)
        elif sort_by == "total":
            agg = agg.sort('total', descending=False)  # Most negative (expenses) first
        else:
            agg = agg.sort('merchant')

        return agg

    def aggregate_by_category(self, sort_by: str = "count") -> pl.DataFrame:
        """Aggregate transactions by category."""
        if self.df is None or len(self.df) == 0:
            return pl.DataFrame()

        agg = self.df.group_by('category').agg([
            pl.count('id').alias('count'),
            pl.sum('amount').alias('total'),
            pl.first('category_id').alias('category_id'),
        ])

        if sort_by == "count":
            agg = agg.sort('count', descending=True)
        elif sort_by == "total":
            agg = agg.sort('total', descending=False)
        else:
            agg = agg.sort('category')

        return agg

    def aggregate_by_group(self, sort_by: str = "count") -> pl.DataFrame:
        """Aggregate transactions by category group."""
        if self.df is None or len(self.df) == 0:
            return pl.DataFrame()

        agg = self.df.group_by('group').agg([
            pl.count('id').alias('count'),
            pl.sum('amount').alias('total'),
        ])

        if sort_by == "count":
            agg = agg.sort('count', descending=True)
        elif sort_by == "total":
            agg = agg.sort('total', descending=False)
        else:
            agg = agg.sort('group')

        return agg

    def filter_by_merchant(self, merchant: str) -> pl.DataFrame:
        """Get all transactions for a specific merchant."""
        if self.df is None:
            return pl.DataFrame()
        return self.df.filter(pl.col('merchant') == merchant).sort('date', descending=True)

    def filter_by_category(self, category: str) -> pl.DataFrame:
        """Get all transactions for a specific category."""
        if self.df is None:
            return pl.DataFrame()
        return self.df.filter(pl.col('category') == category).sort('date', descending=True)

    def filter_by_group(self, group: str) -> pl.DataFrame:
        """Get all transactions for a specific group."""
        if self.df is None:
            return pl.DataFrame()
        return self.df.filter(pl.col('group') == group).sort('date', descending=True)

    def search(self, query: str) -> pl.DataFrame:
        """Fuzzy search across merchants, categories, and notes."""
        if self.df is None or not query:
            return self.df

        query_lower = query.lower()

        # Search in merchant, category, notes
        mask = (
            pl.col('merchant').str.to_lowercase().str.contains(query_lower) |
            pl.col('category').str.to_lowercase().str.contains(query_lower) |
            pl.col('notes').str.to_lowercase().str.contains(query_lower)
        )

        return self.df.filter(mask)

    def add_pending_change(self, transaction_id: str, field: str, value: Any) -> None:
        """Track a pending change."""
        change = {
            'transaction_id': transaction_id,
            'field': field,
            'value': value,
            'timestamp': datetime.now()
        }

        # Add to pending changes
        self.pending_changes.append(change)

        # Update history for undo/redo
        self.change_history = self.change_history[:self.change_index + 1]
        self.change_history.append(change)
        self.change_index += 1

    def undo(self) -> Optional[Dict]:
        """Undo last change."""
        if self.change_index >= 0:
            change = self.change_history[self.change_index]
            self.change_index -= 1
            # Remove from pending if it's there
            if change in self.pending_changes:
                self.pending_changes.remove(change)
            return change
        return None

    def redo(self) -> Optional[Dict]:
        """Redo last undone change."""
        if self.change_index < len(self.change_history) - 1:
            self.change_index += 1
            change = self.change_history[self.change_index]
            if change not in self.pending_changes:
                self.pending_changes.append(change)
            return change
        return None

    async def commit_changes(self, progress_callback=None) -> int:
        """
        Commit all pending changes to Monarch API.

        Returns:
            Number of successfully updated transactions
        """
        if not self.pending_changes:
            return 0

        # Group changes by transaction_id
        changes_by_txn = {}
        for change in self.pending_changes:
            txn_id = change['transaction_id']
            if txn_id not in changes_by_txn:
                changes_by_txn[txn_id] = {}
            changes_by_txn[txn_id][change['field']] = change['value']

        # Build update requests
        update_tasks = []
        for txn_id, updates in changes_by_txn.items():
            kwargs = {'transaction_id': txn_id}

            if 'merchant' in updates:
                kwargs['merchant_name'] = updates['merchant']
            if 'category_id' in updates:
                kwargs['category_id'] = updates['category_id']
            if 'hideFromReports' in updates:
                kwargs['hide_from_reports'] = updates['hideFromReports']
            if 'notes' in updates:
                kwargs['notes'] = updates['notes']

            update_tasks.append(self.mm.update_transaction(**kwargs))

        # Execute all updates in parallel
        if progress_callback:
            progress_callback(0, len(update_tasks), "Saving changes...")

        results = await asyncio.gather(*update_tasks, return_exceptions=True)

        # Count successes
        success_count = sum(1 for r in results if not isinstance(r, Exception))

        if progress_callback:
            progress_callback(len(update_tasks), len(update_tasks),
                            f"Saved {success_count}/{len(update_tasks)} changes")

        # Clear pending changes if all succeeded
        if success_count == len(update_tasks):
            self.pending_changes.clear()

        return success_count

    def get_stats(self) -> Dict[str, Any]:
        """Get summary statistics."""
        if self.df is None or len(self.df) == 0:
            return {
                'total_transactions': 0,
                'total_amount': 0.0,
                'pending_changes': len(self.pending_changes),
            }

        return {
            'total_transactions': len(self.df),
            'total_amount': float(self.df['amount'].sum()),
            'date_range': (
                self.df['date'].min(),
                self.df['date'].max()
            ),
            'unique_merchants': self.df['merchant'].n_unique(),
            'unique_categories': self.df['category'].n_unique(),
            'pending_changes': len(self.pending_changes),
        }
