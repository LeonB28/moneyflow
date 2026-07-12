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
