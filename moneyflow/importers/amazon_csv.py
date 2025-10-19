"""
Amazon purchase CSV importer.

This module handles importing Amazon purchase data from CSV files.
Supports the personal CSV format with columns:
Order Date, Title, Category, Quantity, Item Total, ...
"""

from pathlib import Path
from typing import Dict, Optional, Tuple

import polars as pl

from moneyflow.backends.amazon import AmazonBackend

# Category normalization mapping
CATEGORY_NORMALIZATIONS = {
    "BOoks": "Books",
    "VIdeo Game": "Video Game",
    "Office Products": "Office Product",
}


def normalize_category(category: str) -> str:
    """
    Normalize category names for consistency.

    Args:
        category: Original category name

    Returns:
        Normalized category name
    """
    return CATEGORY_NORMALIZATIONS.get(category, category)


def import_amazon_csv(
    csv_path: str,
    backend: Optional[AmazonBackend] = None,
    force: bool = False,
) -> Dict[str, int]:
    """
    Import Amazon purchases from CSV file.

    Expected CSV columns:
    - Order Date: Date of purchase
    - Title: Item name/description
    - Category: Product category
    - Quantity: Number of items purchased
    - Item Total: Total cost (positive number, will be converted to negative)

    Additional columns are ignored (Reimbursed, Year, Regret, Disposed, Sale Price).

    Args:
        csv_path: Path to Amazon CSV file
        backend: AmazonBackend instance (creates default if None)
        force: If True, re-import duplicates (overwrites existing)

    Returns:
        Dictionary with import statistics:
            - total_rows: Total rows in CSV
            - imported: Number of new transactions imported
            - duplicates: Number of duplicates skipped
            - categories_created: Number of new categories created
    """
    if backend is None:
        backend = AmazonBackend()

    # Read CSV with Polars, treating problematic columns as strings
    # This handles invalid values like "t" in Quantity column
    df = pl.read_csv(
        csv_path,
        schema_overrides={
            "Order Date": pl.Utf8,  # Read as string first (handle multiple formats)
            "Quantity": pl.Utf8,  # Read as string first
            "Item Total": pl.Utf8,  # Read as string first
        },
    )

    # Validate required columns
    required_columns = ["Order Date", "Title", "Category", "Quantity", "Item Total"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

    # Data cleaning and transformation
    # Handle multiple date formats: MM/DD/YYYY, MM/DD/YY, and YYYY-MM-DD (ISO)
    df = df.with_columns(
        [
            # Try ISO format first (YYYY-MM-DD)
            pl.col("Order Date").str.strptime(pl.Date, "%Y-%m-%d", strict=False).alias("date_iso")
        ]
    )

    df = df.with_columns(
        [
            # Try MM/DD/YYYY
            pl.col("Order Date")
            .str.strptime(pl.Date, "%m/%d/%Y", strict=False)
            .alias("date_4digit")
        ]
    )

    df = df.with_columns(
        [
            # Try MM/DD/YY
            pl.col("Order Date")
            .str.strptime(pl.Date, "%m/%d/%y", strict=False)
            .alias("date_2digit")
        ]
    )

    df = df.with_columns(
        [
            # Priority: ISO format > 4-digit year (if valid) > 2-digit year
            # This handles mixed formats in the CSV
            pl.coalesce(
                [
                    "date_iso",
                    pl.when(pl.col("date_4digit").dt.year() >= 1900)
                    .then(pl.col("date_4digit"))
                    .otherwise(pl.col("date_2digit")),
                ]
            ).alias("parsed_date")
        ]
    ).drop(["date_iso", "date_4digit", "date_2digit"])

    # Check for unparseable dates (both formats failed)
    unparseable = df.filter(pl.col("parsed_date").is_null())
    if len(unparseable) > 0:
        bad_rows = unparseable.select(["Order Date", "Title"]).head(10)
        raise ValueError(
            f"Found {len(unparseable)} transactions with unparseable dates.\n"
            f"Expected format: MM/DD/YYYY or MM/DD/YY\n"
            f"First few invalid dates:\n{bad_rows}"
        )

    # Strict validation: Reject dates before 2000 or more than 2 years in future
    from datetime import datetime

    current_year = datetime.now().year

    df = df.with_columns([pl.col("parsed_date").dt.strftime("%Y-%m-%d").alias("date")])

    # Validate date range
    invalid_dates = df.filter(
        (pl.col("parsed_date").dt.year() < 2000)
        | (pl.col("parsed_date").dt.year() > current_year + 2)
    )

    if len(invalid_dates) > 0:
        bad_dates = invalid_dates.select(["Order Date", "date", "Title"]).head(5)
        raise ValueError(
            f"Found {len(invalid_dates)} transactions with invalid dates. "
            f"Dates must be between 2000 and {current_year + 2}.\n"
            f"First few invalid dates:\n{bad_dates}"
        )

    df = df.drop("parsed_date")

    df = df.with_columns(
        [
            # Merchant is the item title
            pl.col("Title").alias("merchant"),
            # Normalize and clean category
            pl.col("Category")
            .fill_null("Misc.")
            .map_elements(normalize_category, return_dtype=pl.Utf8)
            .alias("category"),
            # Convert quantity to integer (strict - will fail on invalid values)
            pl.col("Quantity").cast(pl.Int64).alias("quantity"),
            # Convert Item Total to float, removing $ and commas if present
            pl.col("Item Total")
            .str.replace_all(r"[\$,]", "")
            .cast(pl.Float64, strict=False)
            .fill_null(0.0)
            .mul(-1.0)  # Negate for expenses
            .alias("amount"),
        ]
    )

    # Calculate price per item
    df = df.with_columns([(pl.col("amount") / pl.col("quantity")).alias("price_per_item")])

    # Filter out invalid rows (quantity <= 0)
    df = df.filter(pl.col("quantity") > 0)

    # Select only the columns we need
    df = df.select(
        [
            "date",
            "merchant",
            "category",
            "quantity",
            "amount",
            "price_per_item",
        ]
    )

    total_rows = len(df)
    imported_count = 0
    duplicate_count = 0
    categories_created = 0

    # Connect to database (initializes if needed)
    conn = backend._get_connection()

    # Get existing categories
    existing_categories = set(
        row[0] for row in conn.execute("SELECT name FROM categories").fetchall()
    )

    # Track new categories from this import
    new_categories = set()
    for category in df["category"].unique():
        if category not in existing_categories:
            new_categories.add(category)

    # Insert new categories
    for category in new_categories:
        category_id = category.lower().replace(" ", "_").replace("&", "and")
        conn.execute(
            "INSERT OR IGNORE INTO categories (id, name) VALUES (?, ?)",
            (category_id, category),
        )
        categories_created += 1

    # Get category IDs mapping
    category_id_map = {
        row[1]: row[0] for row in conn.execute("SELECT id, name FROM categories").fetchall()
    }

    # Import transactions
    for row in df.iter_rows(named=True):
        # Generate transaction ID
        txn_id = AmazonBackend.generate_transaction_id(
            date=row["date"],
            merchant=row["merchant"],
            amount=row["amount"],
            quantity=row["quantity"],
        )

        # Check if transaction already exists
        existing = conn.execute("SELECT id FROM transactions WHERE id = ?", (txn_id,)).fetchone()

        if existing and not force:
            duplicate_count += 1
            continue

        # Get category ID
        category_id = category_id_map.get(row["category"])

        # Create notes with quantity info
        notes = f"Qty: {row['quantity']}"

        if existing and force:
            # Update existing transaction
            conn.execute(
                """
                UPDATE transactions
                SET date = ?, merchant = ?, category = ?, category_id = ?,
                    amount = ?, quantity = ?, price_per_item = ?, notes = ?
                WHERE id = ?
            """,
                (
                    row["date"],
                    row["merchant"],
                    row["category"],
                    category_id,
                    row["amount"],
                    row["quantity"],
                    row["price_per_item"],
                    notes,
                    txn_id,
                ),
            )
            duplicate_count += 1
        else:
            # Insert new transaction
            conn.execute(
                """
                INSERT INTO transactions
                (id, date, merchant, category, category_id, amount, quantity,
                 price_per_item, notes, hideFromReports)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """,
                (
                    txn_id,
                    row["date"],
                    row["merchant"],
                    row["category"],
                    category_id,
                    row["amount"],
                    row["quantity"],
                    row["price_per_item"],
                    notes,
                ),
            )
            imported_count += 1

    # Record import in history
    filename = Path(csv_path).name
    conn.execute(
        """
        INSERT INTO import_history (filename, record_count, duplicate_count)
        VALUES (?, ?, ?)
    """,
        (filename, imported_count, duplicate_count),
    )

    conn.commit()
    conn.close()

    return {
        "total_rows": total_rows,
        "imported": imported_count,
        "duplicates": duplicate_count,
        "categories_created": categories_created,
    }


def get_category_statistics(
    backend: Optional[AmazonBackend] = None,
) -> Dict[str, Tuple[int, float]]:
    """
    Get spending statistics by category.

    Args:
        backend: AmazonBackend instance (creates default if None)

    Returns:
        Dictionary mapping category name to (transaction_count, total_amount)
    """
    if backend is None:
        backend = AmazonBackend()

    conn = backend._get_connection()

    cursor = conn.execute("""
        SELECT category, COUNT(*) as count, SUM(amount) as total
        FROM transactions
        GROUP BY category
        ORDER BY total ASC
    """)

    stats = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}
    conn.close()

    return stats
