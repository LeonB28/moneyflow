"""
REST API server implementation for moneyflow.

Exposes the same entry points as the MCP server (moneyflow.mcp.server) through a
FastAPI HTTP interface, allowing HTTP clients and tools to interact with your
financial data.

Security Considerations:
- The REST server runs locally or on a trusted network (e.g., Tailscale)
- Uses the same credential system as the TUI (encrypted or plaintext)
- No built-in authentication - relies on network-level security
- Sensitive financial data is exposed - only run on trusted networks
- Use --read-only mode when you only need to query data

Usage:
    # Run with uvicorn (defaults to http://127.0.0.1:8000)
    python -m moneyflow.rest

    # Run in read-only mode (no modifications allowed)
    python -m moneyflow.rest --read-only

    # Or programmatically
    from moneyflow.rest import create_rest_app
    app = create_rest_app(account_id="your-account-id")
"""

import logging
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import polars as pl

logger = logging.getLogger(__name__)

# Environment variable for encrypted credential password
ENV_PASSWORD = "MONEYFLOW_PASSWORD"

# Security: Maximum number of results to prevent memory issues
MAX_LIMIT = 1000

# Security: Maximum batch size to prevent abuse
MAX_BATCH_SIZE = 100


def _format_amount(amount: float) -> str:
    """Format amount as currency string."""
    if amount < 0:
        return f"-${abs(amount):,.2f}"
    return f"${amount:,.2f}"


def _clamp_limit(limit: int) -> int:
    """Clamp limit to MAX_LIMIT to prevent memory issues."""
    return max(1, min(limit, MAX_LIMIT))


def _df_to_records(df: pl.DataFrame, limit: int = 100) -> List[Dict[str, Any]]:
    """Convert DataFrame to list of records with formatting."""
    if len(df) == 0:
        return []

    # Clamp and apply limit
    limit = _clamp_limit(limit)
    if len(df) > limit:
        df = df.head(limit)

    records = []
    for row in df.iter_rows(named=True):
        record = {
            "id": row.get("id", ""),
            "date": str(row.get("date", "")),
            "merchant": row.get("merchant", ""),
            "category": row.get("category", ""),
            "amount": row.get("amount", 0),
            "amount_formatted": _format_amount(row.get("amount", 0)),
            "account": row.get("account", ""),
        }
        if row.get("notes"):
            record["notes"] = row["notes"]
        if row.get("is_hidden"):
            record["is_hidden"] = True
        records.append(record)

    return records


def create_rest_app(
    account_id: Optional[str] = None,
    config_dir: Optional[str] = None,
    read_only: bool = False,
):
    """
    Create and configure the FastAPI REST server for moneyflow.

    Args:
        account_id: The account ID to use. If None, uses the last active account.
        config_dir: Custom config directory. Defaults to ~/.moneyflow
        read_only: If True, disable all write operations (category updates, etc.)

    Returns:
        Configured FastAPI application instance
    """
    from fastapi import FastAPI

    from ..backends import get_backend
    from ..data.account_manager import AccountManager
    from ..data.credentials import CredentialManager
    from ..data.data_manager import DataManager

    app = FastAPI(
        title="moneyflow REST API",
        description=(
            "Personal finance data and operations, mirroring the moneyflow MCP "
            "server entry points over HTTP."
        ),
        version="0.1.0",
    )

    # State that will be initialized on first use
    _state: Dict[str, Any] = {
        "data_manager": None,
        "transactions_df": None,
        "categories": None,
        "category_groups": None,
        "initialized": False,
        "account_id": account_id,
        "config_dir": config_dir,
        "read_only": read_only,
    }

    async def _ensure_initialized():
        """Lazy initialization of the data manager and data."""
        if _state["initialized"]:
            return

        config_path = Path(_state["config_dir"]) if _state["config_dir"] else None
        account_manager = AccountManager(config_dir=config_path)

        # Get account to use
        if _state["account_id"]:
            account = account_manager.get_account(_state["account_id"])
            if not account:
                raise ValueError(f"Account '{_state['account_id']}' not found")
        else:
            account = account_manager.get_last_active_account()
            if not account:
                raise ValueError("No accounts configured. Run 'moneyflow' to set up.")

        profile_dir = account_manager.get_profile_dir(account.id)
        logger.info(f"Using account: {account.name} ({account.backend_type})")

        # Load credentials
        cred_manager = CredentialManager(config_dir=config_path, profile_dir=profile_dir)

        if not cred_manager.credentials_exist():
            raise ValueError(f"No credentials found for account '{account.id}'")

        # Check if credentials are encrypted
        if cred_manager.is_encrypted():
            # Try to get password from environment variable
            encryption_password = os.environ.get(ENV_PASSWORD)
            if not encryption_password:
                raise ValueError(
                    f"Account '{account.id}' uses encrypted credentials.\n\n"
                    f"The REST server cannot prompt for a password interactively.\n"
                    f"Options:\n"
                    f"  1. Set the {ENV_PASSWORD} environment variable:\n"
                    f"     export {ENV_PASSWORD}='your-password'\n"
                    f"     moneyflow-rest\n\n"
                    f"  2. Use an account with unencrypted credentials:\n"
                    f"     Run 'moneyflow' and set up a new account without password protection\n"
                )
            creds, encryption_key = cred_manager.load_credentials(
                encryption_password=encryption_password
            )
        else:
            # Plaintext credentials - load directly
            creds, encryption_key = cred_manager.load_credentials()

        # Create backend
        backend = get_backend(account.backend_type)

        # Login to backend
        if account.backend_type == "monarch":
            await backend.login(
                email=creds["email"],
                password=creds["password"],
                mfa_secret_key=creds.get("mfa_secret"),
            )
        elif account.backend_type == "ynab":
            # YNAB uses the password field to store the access token
            # Cast to YNABBackend to access the budget_id parameter
            from ..backends.ynab import YNABBackend

            if isinstance(backend, YNABBackend):
                await backend.login(password=creds["password"], budget_id=account.budget_id)
            else:
                await backend.login(password=creds["password"])

        # Create data manager (caching handled separately if needed)
        config_dir_str = str(config_path) if config_path else str(Path.home() / ".moneyflow")
        data_manager = DataManager(
            mm=backend,
            config_dir=config_dir_str,
            profile_dir=profile_dir,
            backend_type=account.backend_type,
        )

        # Fetch data (uses cache if available)
        df, categories, category_groups = await data_manager.fetch_all_data()

        _state["data_manager"] = data_manager
        _state["transactions_df"] = df
        _state["categories"] = categories
        _state["category_groups"] = category_groups
        _state["initialized"] = True
        _state["account"] = account

        logger.info(f"Loaded {len(df)} transactions")

    # ========== QUERY ENDPOINTS ==========

    @app.get("/transactions/search")
    async def search_transactions(
        query: str,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Search transactions by merchant name, category, or notes.

        Args:
            query: Search query (searches merchant, category, and notes)
            limit: Maximum number of results to return (default 50)
        """
        await _ensure_initialized()

        dm = _state["data_manager"]
        df = _state["transactions_df"]

        results = dm.search_transactions(df, query)
        records = _df_to_records(results, limit=limit)

        return {"results": records, "count": len(records)}

    @app.get("/transactions")
    async def get_transactions(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        category: Optional[str] = None,
        merchant: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        Get transactions with optional filters.

        Args:
            start_date: Filter transactions on or after this date (YYYY-MM-DD)
            end_date: Filter transactions on or before this date (YYYY-MM-DD)
            category: Filter by category name (exact match)
            merchant: Filter by merchant name (contains, case-insensitive)
            min_amount: Minimum amount (use negative for expenses)
            max_amount: Maximum amount (use negative for expenses)
            limit: Maximum number of results (default 100)
        """
        await _ensure_initialized()

        df = _state["transactions_df"]

        # Apply filters
        if start_date:
            start_date_dt = datetime.strptime(start_date, "%Y-%m-%d")
            df = df.filter(pl.col("date") >= start_date_dt)
        if end_date:
            end_date_dt = datetime.strptime(end_date, "%Y-%m-%d")
            df = df.filter(pl.col("date") <= end_date_dt)
        if category:
            df = df.filter(pl.col("category") == category)
        if merchant:
            df = df.filter(
                pl.col("merchant").str.to_lowercase().str.contains(merchant.lower(), literal=True)
            )
        if min_amount is not None:
            df = df.filter(pl.col("amount") >= min_amount)
        if max_amount is not None:
            df = df.filter(pl.col("amount") <= max_amount)

        records = _df_to_records(df, limit=limit)
        return {"results": records, "count": len(records)}

    @app.get("/transactions/uncategorized")
    async def get_uncategorized_transactions(
        limit: int = 100,
        merchant: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get transactions that need categorization.

        Finds transactions with category "Uncategorized" that need to be assigned
        to a proper category. Use this to identify items that need attention.

        Args:
            limit: Maximum number of transactions to return (default 100)
            merchant: Optional filter by merchant name (contains, case-insensitive)
        """
        await _ensure_initialized()

        df = _state["transactions_df"]

        # Filter to uncategorized
        uncategorized = df.filter(
            (pl.col("category") == "Uncategorized")
            | (pl.col("category").is_null())
            | (pl.col("category") == "")
        )

        if merchant:
            uncategorized = uncategorized.filter(
                pl.col("merchant").str.to_lowercase().str.contains(merchant.lower(), literal=True)
            )

        records = _df_to_records(uncategorized, limit=limit)
        return {
            "total_uncategorized": len(uncategorized),
            "showing": len(records),
            "transactions": records,
        }

    @app.get("/transactions/{transaction_id}")
    async def get_transaction_details(transaction_id: str) -> Dict[str, Any]:
        """
        Get full details for a specific transaction.

        Returns all available information about a transaction including
        merchant, category, amount, date, account, and any notes.

        Args:
            transaction_id: The ID of the transaction
        """
        await _ensure_initialized()

        df = _state["transactions_df"]

        tx_rows = df.filter(pl.col("id") == transaction_id)
        if len(tx_rows) == 0:
            return {"status": "error", "message": f"Transaction '{transaction_id}' not found"}

        tx = tx_rows.row(0, named=True)

        return {
            "id": tx.get("id"),
            "date": str(tx.get("date")),
            "merchant": tx.get("merchant"),
            "category": tx.get("category"),
            "amount": tx.get("amount"),
            "amount_formatted": _format_amount(tx.get("amount", 0)),
            "account": tx.get("account"),
            "notes": tx.get("notes"),
            "is_hidden": tx.get("is_hidden", False),
        }

    @app.get("/transactions/{transaction_id}/amazon")
    async def get_amazon_order_details(transaction_id: str) -> Dict[str, Any]:
        """
        Look up Amazon order details for a transaction.

        For Amazon transactions, searches local Amazon order database to find
        matching orders and show what items were purchased. This helps with
        categorizing Amazon transactions by revealing the actual products.

        Args:
            transaction_id: The ID of the transaction to look up
        """
        await _ensure_initialized()

        from ..data.amazon_linker import AmazonLinker

        df = _state["transactions_df"]
        config_path = (
            Path(_state["config_dir"]) if _state["config_dir"] else Path.home() / ".moneyflow"
        )

        # Find the transaction
        tx_rows = df.filter(pl.col("id") == transaction_id)
        if len(tx_rows) == 0:
            return {"status": "error", "message": f"Transaction '{transaction_id}' not found"}

        tx = tx_rows.row(0, named=True)
        merchant = tx.get("merchant", "")
        amount = tx.get("amount", 0)
        tx_date = tx.get("date")

        # Create linker and search
        linker = AmazonLinker(config_dir=config_path)

        if not linker.is_amazon_merchant(merchant):
            return {
                "status": "not_amazon",
                "message": f"Transaction merchant '{merchant}' doesn't appear to be Amazon",
                "transaction": {
                    "id": transaction_id,
                    "merchant": merchant,
                    "amount": _format_amount(amount),
                    "date": str(tx_date),
                },
            }

        # Search for matching orders
        matches = linker.find_matching_orders(
            amount=amount,
            transaction_date=str(tx_date),
        )

        if not matches:
            return {
                "status": "no_matches",
                "message": "No matching Amazon orders found in local database",
                "transaction": {
                    "id": transaction_id,
                    "merchant": merchant,
                    "amount": _format_amount(amount),
                    "date": str(tx_date),
                },
                "hint": "Make sure you've imported Amazon order history via the Amazon backend",
            }

        # Format matches
        formatted_matches = []
        for match in matches:
            formatted_matches.append(
                {
                    "order_id": match.order_id,
                    "order_date": match.order_date,
                    "total_amount": _format_amount(match.total_amount),
                    "confidence": match.confidence,
                    "source_profile": match.source_profile,
                    "items": [
                        {
                            "name": item.get("name", "Unknown"),
                            "amount": _format_amount(item.get("amount", 0)),
                            "quantity": item.get("quantity", 1),
                        }
                        for item in match.items
                    ],
                }
            )

        return {
            "status": "found",
            "transaction": {
                "id": transaction_id,
                "merchant": merchant,
                "amount": _format_amount(amount),
                "date": str(tx_date),
                "current_category": tx.get("category", "Uncategorized"),
            },
            "amazon_matches": formatted_matches,
        }

    # ========== CATEGORY ENDPOINTS ==========

    @app.get("/categories")
    async def get_categories() -> Dict[str, Any]:
        """
        Get all available categories and their groups.

        Returns categories organized by group.
        """
        await _ensure_initialized()

        categories = _state["categories"]
        category_groups = [v["name"] for v in _state["category_groups"].values()]

        # Organize categories by group
        by_group: Dict[str, List[str]] = {}
        for cat_id, cat_name in categories.items():
            group_name = cat_name["group"] if cat_name["group"] else "Other"
            if group_name not in by_group:
                by_group[group_name] = []
            by_group[group_name].append(cat_name["name"])

        # Sort categories within groups
        for group in by_group:
            by_group[group].sort()

        return {"groups": category_groups, "categories": by_group}

    @app.get("/merchants")
    async def get_merchants(limit: int = 100) -> Dict[str, Any]:
        """
        Get all merchants with transaction counts.

        Args:
            limit: Maximum number of merchants to return (default 100, max 1000)
        """
        await _ensure_initialized()

        df = _state["transactions_df"]
        limit = _clamp_limit(limit)

        merchant_counts = (
            df.group_by("merchant")
            .agg(
                [
                    pl.col("id").count().alias("transaction_count"),
                    pl.col("amount").sum().alias("total_amount"),
                ]
            )
            .sort("transaction_count", descending=True)
            .head(limit)
        )

        results = []
        for row in merchant_counts.iter_rows(named=True):
            results.append(
                {
                    "merchant": row["merchant"],
                    "transaction_count": row["transaction_count"],
                    "total_amount": _format_amount(row["total_amount"]),
                }
            )

        return {"results": results, "count": len(results)}

    @app.get("/account")
    async def get_account_info() -> Dict[str, Any]:
        """
        Get information about the connected account.

        Returns account information.
        """
        await _ensure_initialized()

        account = _state["account"]
        df = _state["transactions_df"]

        # Calculate date range
        if len(df) > 0:
            date_range = {
                "earliest": str(df["date"].min()),
                "latest": str(df["date"].max()),
            }
        else:
            date_range = {"earliest": None, "latest": None}

        return {
            "account_id": account.id,
            "name": account.name,
            "backend_type": account.backend_type,
            "transaction_count": len(df),
            "date_range": date_range,
            "category_count": len(_state["categories"]),
        }

    @app.get("/spending/summary")
    async def get_spending_summary(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        group_by: str = "category",
    ) -> Dict[str, Any]:
        """
        Get spending summary grouped by category or merchant.

        Args:
            start_date: Start date for the summary (YYYY-MM-DD). Defaults to 30 days ago.
            end_date: End date for the summary (YYYY-MM-DD). Defaults to today.
            group_by: Group spending by "category" or "merchant" (default: category)
        """
        await _ensure_initialized()

        df = _state["transactions_df"]

        # Default date range: last 30 days
        if not end_date:
            end_date = date.today().isoformat()
        if not start_date:
            start_date = (date.today() - timedelta(days=30)).isoformat()

        # Filter by date
        start_date_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_date_dt = datetime.strptime(end_date, "%Y-%m-%d")
        df = df.filter((pl.col("date") >= start_date_dt) & (pl.col("date") <= end_date_dt))

        # Filter to expenses only (negative amounts)
        expenses = df.filter(pl.col("amount") < 0)

        # Group and sum
        group_col = "category" if group_by == "category" else "merchant"
        summary = (
            expenses.group_by(group_col)
            .agg([pl.col("amount").sum().alias("total"), pl.col("id").count().alias("count")])
            .sort("total")  # Sort by total (most negative first = highest spending)
        )

        # Format results
        results = {
            "period": {"start": start_date, "end": end_date},
            "total_spending": _format_amount(expenses["amount"].sum()),
            "transaction_count": len(expenses),
            "by_" + group_by: [],
        }

        for row in summary.iter_rows(named=True):
            results["by_" + group_by].append(
                {
                    group_by: row[group_col],
                    "total": _format_amount(row["total"]),
                    "count": row["count"],
                }
            )

        return results

    # ========== WRITE ENDPOINTS ==========

    @app.post("/transactions/batch/category")
    async def batch_update_category(
        transaction_ids: List[str],
        category_name: str,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Update the category for multiple transactions at once.

        Applies the same category to all specified transactions. Changes are
        immediately committed to the backend API unless dry_run is True.

        Args:
            transaction_ids: List of transaction IDs to update (max 100)
            category_name: The name of the category to assign
            dry_run: If True, validate and show what would change without committing
        """
        await _ensure_initialized()

        # Check read-only mode
        if _state["read_only"] and not dry_run:
            return {
                "status": "error",
                "message": "Server is in read-only mode. Use dry_run=True to preview changes.",
            }

        # Enforce batch size limit
        if len(transaction_ids) > MAX_BATCH_SIZE:
            return {
                "status": "error",
                "message": f"Batch size {len(transaction_ids)} exceeds maximum of {MAX_BATCH_SIZE}",
            }

        dm = _state["data_manager"]
        df = _state["transactions_df"]
        categories = _state["categories"]

        # Find the category ID
        category_id = None
        for cat_id, cat_name in categories.items():
            if cat_name["name"].lower() == category_name.lower():
                category_id = cat_id
                break

        if not category_id:
            return {"status": "error", "message": f"Category '{category_name}' not found"}

        # Find all transactions and validate they exist
        found_transactions = []
        not_found = []
        for tx_id in transaction_ids:
            tx_rows = df.filter(pl.col("id") == tx_id)
            if len(tx_rows) == 0:
                not_found.append(tx_id)
            else:
                tx = tx_rows.row(0, named=True)
                found_transactions.append(
                    {
                        "transaction_id": tx_id,
                        "merchant": tx.get("merchant"),
                        "amount": _format_amount(tx.get("amount", 0)),
                        "date": str(tx.get("date")),
                        "old_category": tx.get("category"),
                    }
                )

        # Dry run - just show what would happen
        if dry_run:
            return {
                "status": "dry_run",
                "message": "No changes made (dry run)",
                "would_update": len(found_transactions),
                "not_found": len(not_found),
                "new_category": category_name,
                "transactions": found_transactions,
                "not_found_ids": not_found if not_found else None,
            }

        success_count = 0
        failure_count = 0
        errors = []

        for tx_id in transaction_ids:
            if tx_id in not_found:
                failure_count += 1
                errors.append({"transaction_id": tx_id, "error": "Transaction not found"})
                continue

            try:
                await dm.mm.update_transaction(
                    transaction_id=tx_id,
                    category_id=category_id,
                )
                success_count += 1
            except Exception as e:
                failure_count += 1
                errors.append({"transaction_id": tx_id, "error": str(e)})

        # Update local DataFrame for successful updates
        if success_count > 0:
            successful_ids = [
                tx_id
                for tx_id in transaction_ids
                if tx_id not in [e["transaction_id"] for e in errors]
            ]
            _state["transactions_df"] = df.with_columns(
                pl.when(pl.col("id").is_in(successful_ids))
                .then(pl.lit(category_name))
                .otherwise(pl.col("category"))
                .alias("category")
            )

        return {
            "status": "success" if failure_count == 0 else "partial",
            "success_count": success_count,
            "failure_count": failure_count,
            "new_category": category_name,
            "errors": errors if errors else None,
        }

    @app.post("/transactions/{transaction_id}/category")
    async def update_transaction_category(
        transaction_id: str,
        category_name: Optional[str] = None,
        category_id: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Update the category of a single transaction.

        Changes the category assignment for a transaction. The change is
        immediately committed to the backend API unless dry_run is True.

        Args:
            transaction_id: The unique ID of the transaction to update
            category_name: The name of the category to assign (use category_id if names are ambiguous)
            category_id: The ID of the category to assign (preferred for disambiguation)
            dry_run: If True, validate and show what would change without committing

        Note: Provide either category_name or category_id, not both. Use category_id
        when multiple categories share the same name.
        """
        await _ensure_initialized()

        # Validate parameters
        if not category_name and not category_id:
            return {
                "status": "error",
                "message": "Either category_name or category_id must be provided",
            }

        if category_name and category_id:
            return {
                "status": "error",
                "message": "Provide either category_name or category_id, not both",
            }

        # Check read-only mode
        if _state["read_only"] and not dry_run:
            return {
                "status": "error",
                "message": "Server is in read-only mode. Use dry_run=True to preview changes.",
            }

        dm = _state["data_manager"]
        df = _state["transactions_df"]
        categories = _state["categories"]

        # Resolve category - by ID or by name
        if category_id:
            # Direct ID lookup
            if category_id not in categories:
                return {"status": "error", "message": f"Category ID '{category_id}' not found"}
            resolved_category_id = category_id
        else:
            # Name lookup with duplicate detection
            matching_categories = [
                (cat_id, cat_name)
                for cat_id, cat_name in categories.items()
                if cat_name["name"].lower() == category_name.lower()
            ]

            if not matching_categories:
                available = sorted(set([c["name"] for c in categories.values()]))
                return {
                    "status": "error",
                    "message": f"Category '{category_name}' not found",
                    "available_categories": available[:50],
                }

            if len(matching_categories) > 1:
                # Multiple categories with same name - require ID for disambiguation
                return {
                    "status": "error",
                    "message": f"Multiple categories named '{category_name}' exist. "
                    "Please use category_id parameter instead.",
                    "matching_categories": [
                        {"id": cat_id, "name": cat_name} for cat_id, cat_name in matching_categories
                    ],
                }

            resolved_category_id = matching_categories[0][0]

        # Get the resolved category name
        resolved_category_name = categories[resolved_category_id]["name"]

        # Find the transaction
        tx_rows = df.filter(pl.col("id") == transaction_id)
        if len(tx_rows) == 0:
            return {"status": "error", "message": f"Transaction '{transaction_id}' not found"}

        old_category = tx_rows["category"][0]
        tx = tx_rows.row(0, named=True)

        # Dry run - just show what would happen
        if dry_run:
            return {
                "status": "dry_run",
                "message": "No changes made (dry run)",
                "would_update": {
                    "transaction_id": transaction_id,
                    "merchant": tx.get("merchant"),
                    "amount": _format_amount(tx.get("amount", 0)),
                    "date": str(tx.get("date")),
                    "old_category": old_category,
                    "new_category": resolved_category_name,
                },
            }

        # Update via backend API
        try:
            await dm.mm.update_transaction(
                transaction_id=transaction_id,
                category_id=resolved_category_id,
            )

            # Update local DataFrame
            _state["transactions_df"] = df.with_columns(
                pl.when(pl.col("id") == transaction_id)
                .then(pl.lit(resolved_category_name))
                .otherwise(pl.col("category"))
                .alias("category")
            )

            return {
                "status": "success",
                "transaction_id": transaction_id,
                "old_category": old_category,
                "new_category": resolved_category_name,
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed to update: {str(e)}"}

    # ========== MAINTENANCE ENDPOINTS ==========

    @app.post("/refresh")
    async def refresh_data() -> Dict[str, Any]:
        """
        Refresh transaction data from the backend API.

        This bypasses the cache and fetches fresh data. Use sparingly
        as it may be rate-limited by the backend.
        """
        await _ensure_initialized()

        dm = _state["data_manager"]

        # Fetch fresh data from API (DataManager doesn't use cache)
        df, categories, category_groups = await dm.fetch_all_data()

        _state["transactions_df"] = df
        _state["categories"] = categories
        _state["category_groups"] = category_groups

        return {
            "status": "success",
            "transaction_count": len(df),
            "refreshed_at": datetime.now().isoformat(),
        }

    @app.get("/health")
    async def health_check() -> Dict[str, str]:
        """Simple health check endpoint."""
        return {"status": "ok"}

    return app


def run_rest_server(
    account_id: Optional[str] = None,
    config_dir: Optional[str] = None,
    host: str = "127.0.0.1",
    port: int = 8000,
    read_only: bool = False,
):
    """
    Run the REST server with uvicorn.

    Args:
        account_id: Account ID to use (defaults to last active)
        config_dir: Custom config directory
        host: Host to bind to (default: 127.0.0.1)
        port: Port to bind to (default: 8000)
        read_only: If True, disable all write operations
    """
    import uvicorn

    app = create_rest_app(account_id=account_id, config_dir=config_dir, read_only=read_only)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_rest_server()
