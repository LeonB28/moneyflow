"""
Tests for DataManager operations including aggregation, filtering, and API integration.
"""

import pytest
import polars as pl
from monarch_tui.data_manager import DataManager


class TestDataFetching:
    """Test data fetching from API."""

    async def test_fetch_all_data(self, data_manager):
        """Test fetching all transactions and metadata."""
        df, categories, category_groups = await data_manager.fetch_all_data()

        assert df is not None
        assert len(df) > 0
        assert isinstance(df, pl.DataFrame)
        assert len(categories) > 0
        assert len(category_groups) > 0

    async def test_fetch_with_date_filter(self, data_manager):
        """Test fetching with date range."""
        df, _, _ = await data_manager.fetch_all_data(start_date="2024-10-01", end_date="2024-10-03")

        assert df is not None
        # Should have filtered transactions
        dates = df["date"].to_list()
        for d in dates:
            assert d.year == 2024
            assert d.month == 10
            assert 1 <= d.day <= 3


class TestAggregation:
    """Test data aggregation functions."""

    async def test_aggregate_by_merchant(self, loaded_data_manager):
        """Test merchant aggregation."""
        dm, df, _, _ = loaded_data_manager

        agg = dm.aggregate_by_merchant(df)

        assert len(agg) > 0
        assert "merchant" in agg.columns
        assert "count" in agg.columns
        assert "total" in agg.columns

        # Should be sorted by count (descending)
        counts = agg["count"].to_list()
        assert counts == sorted(counts, reverse=True)

    async def test_aggregate_by_category(self, loaded_data_manager):
        """Test category aggregation."""
        dm, df, _, _ = loaded_data_manager

        agg = dm.aggregate_by_category(df)

        assert len(agg) > 0
        assert "category" in agg.columns
        assert "count" in agg.columns
        assert "total" in agg.columns
        assert "group" in agg.columns

    async def test_aggregate_by_group(self, loaded_data_manager):
        """Test group aggregation."""
        dm, df, _, _ = loaded_data_manager

        agg = dm.aggregate_by_group(df)

        assert len(agg) > 0
        assert "group" in agg.columns
        assert "count" in agg.columns
        assert "total" in agg.columns

    async def test_aggregate_empty_dataframe(self, data_manager):
        """Test aggregation on empty DataFrame."""
        empty_df = pl.DataFrame()

        agg_merchant = data_manager.aggregate_by_merchant(empty_df)
        agg_category = data_manager.aggregate_by_category(empty_df)
        agg_group = data_manager.aggregate_by_group(empty_df)

        assert agg_merchant.is_empty()
        assert agg_category.is_empty()
        assert agg_group.is_empty()


class TestFiltering:
    """Test data filtering operations."""

    async def test_filter_by_merchant(self, loaded_data_manager):
        """Test filtering by merchant name."""
        dm, df, _, _ = loaded_data_manager

        # Filter by a merchant we know exists
        filtered = dm.filter_by_merchant(df, "Whole Foods")

        assert len(filtered) > 0
        merchants = filtered["merchant"].unique().to_list()
        assert merchants == ["Whole Foods"]

    async def test_filter_by_category(self, loaded_data_manager):
        """Test filtering by category name."""
        dm, df, _, _ = loaded_data_manager

        filtered = dm.filter_by_category(df, "Groceries")

        assert len(filtered) > 0
        categories = filtered["category"].unique().to_list()
        assert categories == ["Groceries"]

    async def test_filter_by_group(self, loaded_data_manager):
        """Test filtering by group name."""
        dm, df, _, _ = loaded_data_manager

        filtered = dm.filter_by_group(df, "Food & Dining")

        assert len(filtered) > 0
        groups = filtered["group"].unique().to_list()
        assert groups == ["Food & Dining"]

    async def test_search_transactions(self, loaded_data_manager):
        """Test search functionality."""
        dm, df, _, _ = loaded_data_manager

        # Search for "starbucks"
        results = dm.search_transactions(df, "starbucks")

        assert len(results) > 0
        # All results should contain "starbucks" in merchant, category, or notes
        for row in results.iter_rows(named=True):
            text = f"{row['merchant']} {row['category']} {row['notes']}".lower()
            assert "starbucks" in text

    async def test_search_empty_query(self, loaded_data_manager):
        """Test search with empty query returns all."""
        dm, df, _, _ = loaded_data_manager

        results = dm.search_transactions(df, "")

        assert len(results) == len(df)


class TestCommitEdits:
    """Test committing pending edits to the API."""

    async def test_commit_single_edit(self, data_manager, mock_mm):
        """Test committing a single edit."""
        from monarch_tui.state import TransactionEdit
        from datetime import datetime

        edits = [
            TransactionEdit(
                transaction_id="txn_1",
                field="merchant",
                old_value="Old Name",
                new_value="New Name",
                timestamp=datetime.now(),
            )
        ]

        success, failure = await data_manager.commit_pending_edits(edits)

        assert success == 1
        assert failure == 0
        assert len(mock_mm.update_calls) == 1

        # Verify the update call
        call = mock_mm.update_calls[0]
        assert call["transaction_id"] == "txn_1"
        assert call["merchant_name"] == "New Name"

    async def test_commit_multiple_edits(self, data_manager, mock_mm):
        """Test committing multiple edits."""
        from monarch_tui.state import TransactionEdit
        from datetime import datetime

        edits = [
            TransactionEdit("txn_1", "merchant", "A", "B", datetime.now()),
            TransactionEdit("txn_2", "category", "cat_old", "cat_new", datetime.now()),
            TransactionEdit("txn_3", "hide_from_reports", False, True, datetime.now()),
        ]

        success, failure = await data_manager.commit_pending_edits(edits)

        assert success == 3
        assert failure == 0
        assert len(mock_mm.update_calls) == 3

    async def test_commit_empty_edits(self, data_manager, mock_mm):
        """Test committing with no edits."""
        success, failure = await data_manager.commit_pending_edits([])

        assert success == 0
        assert failure == 0
        assert len(mock_mm.update_calls) == 0

    async def test_commit_merchant_rename(self, data_manager, mock_mm):
        """Test committing a merchant rename."""
        from monarch_tui.state import TransactionEdit
        from datetime import datetime

        edits = [TransactionEdit("txn_1", "merchant", "Amazon.com", "Amazon", datetime.now())]

        await data_manager.commit_pending_edits(edits)

        # Verify the transaction was updated in mock backend
        txn = mock_mm.get_transaction_by_id("txn_1")
        assert txn is not None
        assert txn["merchant"]["name"] == "Amazon"

    async def test_commit_category_change(self, data_manager, mock_mm):
        """Test committing a category change."""
        from monarch_tui.state import TransactionEdit
        from datetime import datetime

        edits = [
            TransactionEdit("txn_1", "category", "cat_groceries", "cat_shopping", datetime.now())
        ]

        await data_manager.commit_pending_edits(edits)

        # Verify the transaction was updated
        txn = mock_mm.get_transaction_by_id("txn_1")
        assert txn is not None
        assert txn["category"]["id"] == "cat_shopping"

    async def test_commit_hide_toggle(self, data_manager, mock_mm):
        """Test committing hide from reports toggle."""
        from monarch_tui.state import TransactionEdit
        from datetime import datetime

        edits = [TransactionEdit("txn_1", "hide_from_reports", False, True, datetime.now())]

        await data_manager.commit_pending_edits(edits)

        # Verify the transaction was updated
        txn = mock_mm.get_transaction_by_id("txn_1")
        assert txn is not None
        assert txn["hideFromReports"] is True


class TestCategoryGroupMapping:
    """Test category to group mapping."""

    def test_category_mapping_exists(self, data_manager):
        """Test that category to group mapping is initialized."""
        assert len(data_manager.category_to_group) > 0

    def test_groceries_mapped_to_food(self, data_manager):
        """Test that Groceries maps to Food & Dining."""
        assert data_manager.category_to_group.get("Groceries") == "Food & Dining"

    def test_gas_mapped_to_transportation(self, data_manager):
        """Test that Gas maps to Transportation."""
        assert data_manager.category_to_group.get("Gas") == "Transportation"

    async def test_transactions_have_groups(self, loaded_data_manager):
        """Test that loaded transactions have group field."""
        dm, df, _, _ = loaded_data_manager

        assert "group" in df.columns
        groups = df["group"].unique().to_list()
        assert len(groups) > 0
        assert all(g is not None for g in groups)
