"""
Amazon purchase CSV importer.

This module handles importing Amazon purchase data from CSV files.
Supports the personal CSV format with columns:
Order Date, Title, Category, Quantity, Item Total, ...
"""

import sqlite3
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

    # Read CSV with Polars
    df = pl.read_csv(csv_path)

    # Validate required columns
    required_columns = ["Order Date", "Title", "Category", "Quantity", "Item Total"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

    # Data cleaning and transformation
    df = df.with_columns([
        # Parse date to ISO format
        pl.col("Order Date").str.to_date("%m/%d/%Y").dt.strftime("%Y-%m-%d").alias("date"),

        # Merchant is the item title
        pl.col("Title").alias("merchant"),

        # Normalize and clean category
        pl.col("Category").fill_null("Misc.").map_elements(
            normalize_category, return_dtype=pl.Utf8
        ).alias("category"),

        # Convert quantity to integer
        pl.col("Quantity").cast(pl.Int64).alias("quantity"),

        # Convert Item Total to negative float (expenses are negative in moneyflow)
        (pl.col("Item Total") * -1.0).alias("amount"),
    ])

    # Calculate price per item
    df = df.with_columns([
        (pl.col("amount") / pl.col("quantity")).alias("price_per_item")
    ])

    # Filter out invalid rows (quantity <= 0)
    df = df.filter(pl.col("quantity") > 0)

    # Select only the columns we need
    df = df.select([
        "date",
        "merchant",
        "category",
        "quantity",
        "amount",
        "price_per_item",
    ])

    total_rows = len(df)
    imported_count = 0
    duplicate_count = 0
    categories_created = 0

    # Connect to database
    conn = sqlite3.connect(backend.db_path)

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
        row[1]: row[0]
        for row in conn.execute("SELECT id, name FROM categories").fetchall()
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
        existing = conn.execute(
            "SELECT id FROM transactions WHERE id = ?", (txn_id,)
        ).fetchone()

        if existing and not force:
            duplicate_count += 1
            continue

        # Get category ID
        category_id = category_id_map.get(row["category"])

        # Create notes with quantity info
        notes = f"Qty: {row['quantity']}"

        if existing and force:
            # Update existing transaction
            conn.execute("""
                UPDATE transactions
                SET date = ?, merchant = ?, category = ?, category_id = ?,
                    amount = ?, quantity = ?, price_per_item = ?, notes = ?
                WHERE id = ?
            """, (
                row["date"],
                row["merchant"],
                row["category"],
                category_id,
                row["amount"],
                row["quantity"],
                row["price_per_item"],
                notes,
                txn_id,
            ))
            duplicate_count += 1
        else:
            # Insert new transaction
            conn.execute("""
                INSERT INTO transactions
                (id, date, merchant, category, category_id, amount, quantity,
                 price_per_item, notes, hideFromReports)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """, (
                txn_id,
                row["date"],
                row["merchant"],
                row["category"],
                category_id,
                row["amount"],
                row["quantity"],
                row["price_per_item"],
                notes,
            ))
            imported_count += 1

    # Record import in history
    filename = Path(csv_path).name
    conn.execute("""
        INSERT INTO import_history (filename, record_count, duplicate_count)
        VALUES (?, ?, ?)
    """, (filename, imported_count, duplicate_count))

    conn.commit()
    conn.close()

    return {
        "total_rows": total_rows,
        "imported": imported_count,
        "duplicates": duplicate_count,
        "categories_created": categories_created,
    }


def get_category_statistics(backend: Optional[AmazonBackend] = None) -> Dict[str, Tuple[int, float]]:
    """
    Get spending statistics by category.

    Args:
        backend: AmazonBackend instance (creates default if None)

    Returns:
        Dictionary mapping category name to (transaction_count, total_amount)
    """
    if backend is None:
        backend = AmazonBackend()

    conn = sqlite3.connect(backend.db_path)

    cursor = conn.execute("""
        SELECT category, COUNT(*) as count, SUM(amount) as total
        FROM transactions
        GROUP BY category
        ORDER BY total ASC
    """)

    stats = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}
    conn.close()

    return stats
