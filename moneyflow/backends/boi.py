from typing import Any, Dict, List, Optional
import polars as pl
from .base import FinanceBackend
import datetime
import uuid


class BankOfIreland(FinanceBackend):
    def __init__(self, profile_dir: Optional[str] = None):
        self.base_path = "/Users/leon.bam/boi"

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

        ldf = self.__read_data()
        if start_date:
            ldf = ldf.filter(pl.col("Date") >= datetime.datetime.strptime(start_date, "%Y-%m-%d"))

        if end_date:
            ldf = ldf.filter(pl.col("Date") <= datetime.datetime.strptime(end_date, "%Y-%m-%d"))

        ldf = ldf.limit(limit).slice(offset)
        ldf = self._parse_details(ldf)
        with_categories = self._read_merchant_categories().join(
            ldf,
            left_on="merchant",
            right_on="Details",
            how="right",
        ).join(
            self._read_categories(),
            left_on="category_id",
            right_on="category_id",
            how="left",
        ).with_columns(
            Details=pl.coalesce(pl.col("display_name").cast(pl.String),pl.col("Details"))
        )
        df = with_categories.collect(engine="streaming")
        res = df.to_dicts()
        total_count = len(res)
        results = [
            {
                "id": i + 1,
                "date": row["Date"].strftime("%Y-%m-%d"),
                "amount": row["Credit"] if row["Credit"] else -1 * row["Debit"],
                "merchant": {"id": i + 1, "name": row["Details"]},
                "account": {"id": 1, "name": "meme"},
                "category": {"id": row["category_id"], "name": row["category_name"]},
                "notes": None,
                "hideFromReports": False,
                "pending": False,
                "isRecurring": False,
            }
            for i, row in enumerate(res)
        ]
        return {"allTransactions": {"results": results, "totalCount": total_count}}

    async def get_transaction_categories(self) -> Dict[str, Any]:
        read_categories = self._read_categories()
        print(read_categories)
        d = read_categories.collect().to_dicts()
        categories = [{"id": r["category_id"], "name": r["category_name"], "group": {

        }} for r in d]
        return {"categories": categories}

    async def get_transaction_category_groups(self) -> Dict[str, Any]:
        ldf = pl.scan_csv(f"{self.base_path}/categories/group.csv")
        d = ldf.collect().to_dicts()
        category_groups = [
            {"id": r["group_id"], "name": r["group_name"], "type": r["type"]}
            for r in d
        ]
        return {
            "categoryGroups": category_groups
        }

    def _read_merchant_categories(self):
        return pl.scan_csv(f"{self.base_path}/categories/merchant.csv")

    def _read_categories(self) -> pl.LazyFrame:
        category_ldf =  pl.scan_csv(f"{self.base_path}/categories/category.csv")
        group_ldf = pl.scan_csv(f"{self.base_path}/categories/group.csv")
        return category_ldf.join(
            group_ldf,
            left_on="id",
            right_on="group_id",
            how="left"
        ).select(
            category_id=pl.col("id"),
            category_name=pl.col("name"),
            category_group_name=pl.col("group_name")
        )





    async def update_transaction(
        self,
        transaction_id: str,
        merchant_name: Optional[str] = None,
        category_id: Optional[str] = None,
        hide_from_reports: Optional[bool] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        pass

    async def delete_transaction(self, transaction_id: str) -> bool:
        pass

    async def get_all_merchants(self) -> List[str]:
        ldf = self.__read_data()
        ldf = self._parse_details(ldf)
        res = ldf.collect(engine="streaming").to_dicts()
        return [row["Details"] for row in res]

    def get_backend_type(self) -> str:
        return "bankofireland"

    def __read_data(self) -> pl.LazyFrame:
        return pl.scan_csv(
            f"{self.base_path}/transactions/*.csv",
            schema={
                "Date": pl.Date,
                "Details": pl.String,
                "Debit": pl.Float16,
                "Credit": pl.Float16,
                "Balance": pl.Float32,
            },
        )


    def _parse_details(self, ldf: pl.LazyFrame) -> pl.LazyFrame:
        return ldf.with_columns(
            Details=self._parse_details_dates(
                pl.col("Details")
            ).pipe(
                self._parse_sum
            )
        )

    @staticmethod
    def _parse_details_dates(exp: pl.Expr) -> pl.Expr:
        as_arr = exp.str.split(" ")
        return pl.when(
            as_arr.list.first().str.contains("\d{2}(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)")
        ).then(as_arr.list.slice(1)).otherwise(as_arr).list.join(" ")

    @staticmethod
    def _parse_sum(exp: pl.Expr) -> pl.Expr:
        return pl.when(
            exp == "SUMUP  *BAX"
        ).then(
            pl.lit("MasterCardFood")
        ).otherwise(exp)
async def get():
    import asyncio
    boi = BankOfIreland()
    ldf = await boi.get_transactions()
    print(ldf)

if __name__ == '__main__':
    get()
