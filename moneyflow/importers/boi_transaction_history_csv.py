import datetime

import duckdb
import polars as pl
from moneyflow.backends.boi import BankOfIreland


class BoiHistoryImporter:
    def __init__(self, path: str, backend: BankOfIreland):
        self.history_path = path
        self.backend = backend

    def import_boi_history(self):
        transactions_ldf = self._read_history_csv()
        with self.backend.get_connection() as conn:
            transformed_df = transactions_ldf.select(
                date=pl.col("date").cast(pl.Date),
                merchant=pl.lit(None, pl.String),
                details=pl.col("details"),
                debit=pl.col("debit").cast(pl.Float32),
                credit=pl.col("credit").cast(pl.Float32),
                file_name=pl.lit(self.history_path.split("/")[-1]),
                inserted_at=datetime.datetime.now()
            ).collect(engine="streaming")

            conn.execute("""
                MERGE INTO transactions
                using (
                    SELECT 
                        nextval('seq_transaction_id') as id,
                        date,
                        merchant,
                        debit,
                        credit,
                        details,
                        file_name,
                        inserted_at
                    FROM transformed_df
                ) as updates
                on (
                    transactions.date = updates.date
                    AND transactions.details = updates.details 
                    AND transactions.details IS NOT DISTINCT FROM updates.details
                    AND transactions.credit IS NOT DISTINCT FROM updates.credit
                )
                WHEN MATCHED AND transactions.file_name != updates.file_name THEN
                    -- same transaction in different file 
                    UPDATE SET file_name = updates.file_name 
                WHEN MATCHED AND (
                    transactions.file_name = updates.file_name
                    AND transactions.inserted_at != updates.inserted_at
                ) THEN 
                -- rerun same file
                UPDATE SET inserted_at = updates.inserted_at
                -- new transaction
                WHEN NOT MATCHED THEN INSERT;
            """).commit()

    def update_merchant(self):
        transactions_ldf = self._read_history_csv()
        with_merchant_ldf = self.__with_merchant_computed(transactions_ldf)
        updates_df = with_merchant_ldf.select(
            pl.col("details"),
            pl.col("merchant"),
        ).collect(engine="streaming")

        with self.backend.get_connection() as conn:
            conn.execute("""
                MERGE INTO transactions
                USING ( 
                    SELECT 
                        details, merchant
                    FROM
                        updates_df
                    ) as updates
                ON (transactions.details = updates.details)
                WHEN MATCHED THEN UPDATE
                    SET merchant = updates.merchant
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
            credit=pl.col("Credit")
        )

    def __with_merchant_computed(self, ldf: pl.LazyFrame) -> pl.LazyFrame:
        return ldf.with_columns(
            merchant=
            self._parse_details_dates(pl.col("details"))
            .pipe(self._parse_by_name)
        )

    @staticmethod
    def _parse_details_dates(exp: pl.Expr) -> pl.Expr:
        as_arr = exp.str.split(" ")
        return (
            pl.when(
                as_arr.list.first().str.contains(
                    "\d{2}(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)"
                )
            )
            .then(as_arr.list.slice(1))
            .otherwise(as_arr)
            .list.join(" ")
        )

    @staticmethod
    def _parse_by_name(exp: pl.Expr) -> pl.Expr:
        return (
            pl.when(exp == "SUMUP  *BAX")
            .then(pl.lit("MasterCardFood"))
            .when(exp.str.starts_with("LHC"))
            .then(pl.lit("Laya"))
            .when(exp.str.starts_with("ENROLMY"))
            .then(pl.lit("Sherpa"))
            .when(
                exp.str.starts_with("V01675867") &
                exp.str.ends_with("QB SP")
            ).then(pl.lit("Child Benefits"))
            .otherwise(exp)
        )