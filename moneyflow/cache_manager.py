"""
Cache manager for storing and retrieving transaction data.

Caches transaction DataFrames to disk for faster subsequent loads.
Tracks filter parameters to ensure cache matches user's request.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import polars as pl


class CacheManager:
    """Manage caching of transaction data to disk."""

    CACHE_VERSION = "1.0"
    CACHE_MAX_AGE_HOURS = 24

    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize cache manager.

        Args:
            cache_dir: Directory for cache files. Defaults to ~/.moneyflow/cache/
        """
        if cache_dir:
            self.cache_dir = Path(cache_dir).expanduser()
        else:
            self.cache_dir = Path.home() / ".moneyflow" / "cache"

        # Create cache directory if it doesn't exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.transactions_file = self.cache_dir / "transactions.parquet"
        self.metadata_file = self.cache_dir / "metadata.json"
        self.categories_file = self.cache_dir / "categories.json"

    def cache_exists(self) -> bool:
        """Check if cache files exist."""
        return (
            self.transactions_file.exists()
            and self.metadata_file.exists()
            and self.categories_file.exists()
        )

    def is_cache_valid(self, year: Optional[int] = None, since: Optional[str] = None) -> bool:
        """
        Check if cache is valid for the requested parameters.

        Args:
            year: Year filter from CLI (if any)
            since: Since date filter from CLI (if any)

        Returns:
            True if cache exists and matches parameters, False otherwise
        """
        if not self.cache_exists():
            return False

        try:
            metadata = self.load_metadata()

            # Check version matches
            if metadata.get("version") != self.CACHE_VERSION:
                return False

            # Check parameters match
            cached_year = metadata.get("year_filter")
            cached_since = metadata.get("since_filter")

            # Parameters must match exactly
            if cached_year != year or cached_since != since:
                return False

            return True

        except Exception:
            return False

    def get_cache_age_hours(self) -> Optional[float]:
        """Get age of cache in hours."""
        if not self.metadata_file.exists():
            return None

        try:
            metadata = self.load_metadata()
            fetch_time = datetime.fromisoformat(metadata["fetch_timestamp"])
            age = datetime.now() - fetch_time
            return age.total_seconds() / 3600
        except Exception:
            return None

    def load_metadata(self) -> Dict[str, Any]:
        """Load cache metadata."""
        with open(self.metadata_file, "r") as f:
            return json.load(f)

    def save_cache(
        self,
        transactions_df: pl.DataFrame,
        categories: Dict,
        category_groups: Dict,
        year: Optional[int] = None,
        since: Optional[str] = None,
    ) -> None:
        """
        Save transaction data to cache.

        Args:
            transactions_df: Polars DataFrame of transactions
            categories: Dict of categories
            category_groups: Dict of category groups
            year: Year filter used (if any)
            since: Since date filter used (if any)
        """
        # Save DataFrame as Parquet (fast, compressed, native Polars)
        transactions_df.write_parquet(self.transactions_file)

        # Save categories and groups as JSON
        cache_data = {
            "categories": categories,
            "category_groups": category_groups,
        }
        with open(self.categories_file, "w") as f:
            json.dump(cache_data, f, indent=2)

        # Save metadata
        metadata = {
            "version": self.CACHE_VERSION,
            "fetch_timestamp": datetime.now().isoformat(),
            "year_filter": year,
            "since_filter": since,
            "total_transactions": len(transactions_df),
        }
        with open(self.metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

    def load_cache(self) -> Optional[Tuple[pl.DataFrame, Dict, Dict, Dict]]:
        """
        Load cached transaction data.

        Returns:
            Tuple of (transactions_df, categories, category_groups, metadata) or None if cache invalid
        """
        if not self.cache_exists():
            return None

        try:
            # Load DataFrame from Parquet
            transactions_df = pl.read_parquet(self.transactions_file)

            # Load categories and groups
            with open(self.categories_file, "r") as f:
                cache_data = json.load(f)
            categories = cache_data["categories"]
            category_groups = cache_data["category_groups"]

            # Load metadata
            metadata = self.load_metadata()

            return transactions_df, categories, category_groups, metadata

        except Exception as e:
            print(f"Warning: Failed to load cache: {e}")
            return None

    def clear_cache(self) -> None:
        """Delete all cache files."""
        files = [self.transactions_file, self.metadata_file, self.categories_file]
        for file in files:
            if file.exists():
                file.unlink()

    def get_cache_info(self) -> Optional[Dict[str, Any]]:
        """
        Get human-readable cache information.

        Returns:
            Dict with cache info or None if no cache
        """
        if not self.cache_exists():
            return None

        try:
            metadata = self.load_metadata()
            age_hours = self.get_cache_age_hours()

            # Format age nicely
            if age_hours is None:
                age_str = "Unknown"
            elif age_hours < 1:
                age_str = f"{int(age_hours * 60)} minutes ago"
            elif age_hours < 24:
                age_str = f"{int(age_hours)} hours ago"
            else:
                age_str = f"{int(age_hours / 24)} days ago"

            # Format filters
            if metadata.get("year_filter"):
                filter_str = f"Year {metadata['year_filter']} onwards"
            elif metadata.get("since_filter"):
                filter_str = f"Since {metadata['since_filter']}"
            else:
                filter_str = "All transactions"

            return {
                "age": age_str,
                "age_hours": age_hours,
                "transaction_count": metadata.get("total_transactions", 0),
                "filter": filter_str,
                "timestamp": metadata.get("fetch_timestamp"),
            }

        except Exception:
            return None
