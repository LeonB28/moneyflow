from unittest.mock import MagicMock, patch

import pytest

from moneyflow.backends.boi import BankOfIreland


class TestBoiBackend:
    @pytest.fixture
    def backend(self):
        return BankOfIreland()

    @pytest.mark.asyncio
    async def test_get_transactions(self, backend):
        result = await backend.get_transactions(limit=100, offset=0, hidden_from_reports=False)
        print(result)

    async def test_get_categor(self, backend):
        result = await backend.get_transaction_categories()
        print(result)

    async def test_get_group(self, backend):
        result = await backend.get_transaction_category_groups()
        print(result)

    @pytest.mark.asyncio
    async def test_get_transactions_null_credit_and_debit(self, backend):
        """Rows with NULL credit AND debit (e.g. balance markers) must not crash."""
        mock_rows = [
            {
                "id": "tx-credit",
                "date": "2026-08-10",
                "credit": 100.0,
                "debit": None,
                "merchant": "Example Employer",
                "category": "Income",
                "category_id": "cat_income",
                "file_name": "statement.csv",
            },
            {
                "id": "tx-debit",
                "date": "2026-08-11",
                "credit": None,
                "debit": 25.5,
                "merchant": "Example Store",
                "category": "Groceries",
                "category_id": "cat_groceries",
                "file_name": "statement.csv",
            },
            {
                "id": "tx-nulls",
                "date": "2026-08-12",
                "credit": None,
                "debit": None,
                "merchant": "Balance Marker",
                "category": "Uncategorized",
                "category_id": "cat_uncategorized",
                "file_name": "statement.csv",
            },
        ]
        mock_pl = MagicMock()
        mock_pl.to_dicts.return_value = mock_rows
        mock_conn = MagicMock()
        mock_conn.execute.return_value.pl.return_value = mock_pl
        mock_conn.__enter__ = lambda s: mock_conn
        mock_conn.__exit__ = lambda *a: False

        with patch.object(BankOfIreland, "get_connection", return_value=mock_conn):
            result = await backend.get_transactions(limit=100, offset=0)

        results = result["allTransactions"]["results"]
        assert len(results) == 3
        assert results[0]["amount"] == 100.0
        assert results[1]["amount"] == -25.5
        # NULL/NULL row must default to 0 instead of raising TypeError
        assert results[2]["amount"] == 0
