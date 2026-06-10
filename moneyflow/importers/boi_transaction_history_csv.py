import duckdb
import polars as pl
from moneyflow.backends.boi import BankOfIreland

class BoiHistoryImporter():

    def __init__(self, path: str, backend: BankOfIreland):
        self.history_path = path
        self.backend = backend

    def import_boi_history(self):
        transactions_ldf = self._read_history_csv()
        transformed_ldf = self.__transform_transactions(transactions_ldf)
        with self.backend.get_connection() as conn:
            transformed_df = transformed_ldf.select(
                date=pl.col("date").cast(pl.Date),
                details=pl.col("details"),
                debit=pl.col("debit").cast(pl.Float32),
                credit=pl.col("credit").cast(pl.Float32),
            ).collect(engine="streaming")
            conn.execute("""
                INSERT INTO transactions
                SELECT 
                    nextval('seq_transaction_id') as id,
                    date,
                    details,
                    'Uncategorized' as category,
                    'cat_uncategorized' as category_id,
                    debit,
                    credit
                FROM transformed_df
            """).commit()

    def _read_history_csv(self) -> pl.LazyFrame:
        return pl.scan_csv(
            self.history_path,
            schema={
                "Date": pl.Date,
                "Details": pl.String,
                "Debit": pl.Float16,
                "Credit": pl.Float16,
                "Balance": pl.Float32,
            },
        ).select(
            date=pl.col("Date"),
            details=pl.col("Details"),
            debit=pl.col("Debit"),
            credit=pl.col("Credit"),
        )

    def __transform_transactions(self, ldf: pl.LazyFrame) -> pl.LazyFrame:
        return ldf.with_columns(
            details=self._parse_details_dates(
                pl.col("details")
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

