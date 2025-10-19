"""
Modal parameter helpers for consistent and testable modal dialogs.

This module provides functions that prepare parameters for modal dialogs,
making the logic testable without requiring the UI to be running.

Each function returns a dictionary of parameters that can be unpacked
when creating modal screens.
"""

from typing import Any, Dict, Optional

import polars as pl


class ModalHelper:
    """
    Helper class for preparing modal dialog parameters.

    All methods are static and return dictionaries that can be unpacked
    into modal screen constructors.

    Example:
        params = ModalHelper.edit_merchant_params(merchant, count, all_merchants)
        result = await self.push_screen(EditMerchantScreen(**params), wait_for_dismiss=True)
    """

    # ==================== Edit Merchant ====================

    @staticmethod
    def edit_merchant_params(
        merchant_name: str,
        transaction_count: int,
        all_merchants: list[str],
        bulk_summary: Optional[Dict[str, Any]] = None,
        txn_details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Prepare parameters for Edit Merchant modal.

        Args:
            merchant_name: Current merchant name
            transaction_count: Number of transactions affected
            all_merchants: List of all merchants for autocomplete
            bulk_summary: Optional dict with "total_amount" for bulk edits
            txn_details: Optional dict with "date", "amount", "category" for single edit

        Returns:
            Dictionary ready to unpack into EditMerchantScreen constructor
        """
        params = {
            "current_merchant": merchant_name,
            "transaction_count": transaction_count,
            "all_merchants": all_merchants,
        }

        if bulk_summary is not None:
            params["bulk_summary"] = bulk_summary

        if txn_details is not None:
            params["txn_details"] = txn_details

        return params

    # ==================== Select Category ====================

    @staticmethod
    def select_category_params(
        categories: dict,
        current_category_id: Optional[str] = None,
        txn_details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Prepare parameters for Category Selection modal.

        Args:
            categories: Dictionary of category_id -> category info
            current_category_id: Currently selected category (if any)
            txn_details: Optional dict with "date", "amount", "merchant" for context

        Returns:
            Dictionary ready to unpack into SelectCategoryScreen constructor
        """
        params = {
            "categories": categories,
            "current_category_id": current_category_id,
        }

        if txn_details is not None:
            params["txn_details"] = txn_details

        return params

    # ==================== Review Changes ====================

    @staticmethod
    def review_changes_params(edits: list, categories: dict) -> Dict[str, Any]:
        """
        Prepare parameters for Review Changes modal.

        Args:
            edits: List of TransactionEdit objects
            categories: Dictionary of category_id -> category info

        Returns:
            Dictionary ready to unpack into ReviewChangesScreen constructor
        """
        return {
            "edits": edits,
            "categories": categories,
        }

    # ==================== Delete Confirmation ====================

    @staticmethod
    def delete_confirmation_params(transaction_count: int = 1) -> Dict[str, Any]:
        """
        Prepare parameters for Delete Confirmation modal.

        Args:
            transaction_count: Number of transactions to delete

        Returns:
            Dictionary ready to unpack into DeleteConfirmationScreen constructor
        """
        return {
            "transaction_count": transaction_count,
        }

    # ==================== Quit Confirmation ====================

    @staticmethod
    def quit_confirmation_params(has_unsaved_changes: bool) -> Dict[str, Any]:
        """
        Prepare parameters for Quit Confirmation modal.

        Args:
            has_unsaved_changes: Whether there are pending changes

        Returns:
            Dictionary ready to unpack into QuitConfirmationScreen constructor
        """
        return {
            "has_unsaved_changes": has_unsaved_changes,
        }

    # ==================== Filter Settings ====================

    @staticmethod
    def filter_params(show_transfers: bool, show_hidden: bool) -> Dict[str, Any]:
        """
        Prepare parameters for Filter Settings modal.

        Args:
            show_transfers: Whether to show transfer transactions
            show_hidden: Whether to show hidden transactions

        Returns:
            Dictionary ready to unpack into FilterScreen constructor
        """
        return {
            "show_transfers": show_transfers,
            "show_hidden": show_hidden,
        }

    # ==================== Search ====================

    @staticmethod
    def search_params(current_query: str = "") -> Dict[str, Any]:
        """
        Prepare parameters for Search modal.

        Args:
            current_query: Current search query

        Returns:
            Dictionary ready to unpack into SearchScreen constructor
        """
        return {
            "current_query": current_query,
        }

    # ==================== Cache Prompt ====================

    @staticmethod
    def cache_prompt_params(age: str, transaction_count: int, filter_desc: str) -> Dict[str, Any]:
        """
        Prepare parameters for Cache Prompt modal.

        Args:
            age: Human-readable cache age (e.g., "2 hours ago")
            transaction_count: Number of transactions in cache
            filter_desc: Description of filters applied to cache

        Returns:
            Dictionary ready to unpack into CachePromptScreen constructor
        """
        return {
            "age": age,
            "transaction_count": transaction_count,
            "filter_desc": filter_desc,
        }

    # ==================== Transaction Details ====================

    @staticmethod
    def transaction_detail_params(transaction: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare parameters for Transaction Detail modal.

        Args:
            transaction: Dictionary with transaction data

        Returns:
            Dictionary ready to unpack into TransactionDetailScreen constructor
        """
        return {
            "transaction": transaction,
        }

    # ==================== Duplicates ====================

    @staticmethod
    def duplicates_params(
        duplicates_df: pl.DataFrame, duplicate_groups: list, all_transactions_df: pl.DataFrame
    ) -> Dict[str, Any]:
        """
        Prepare parameters for Duplicates modal.

        Args:
            duplicates_df: DataFrame of duplicate transactions
            duplicate_groups: List of duplicate groups
            all_transactions_df: Full DataFrame for context

        Returns:
            Dictionary ready to unpack into DuplicatesScreen constructor
        """
        return {
            "duplicates": duplicates_df,
            "groups": duplicate_groups,
            "all_transactions": all_transactions_df,
        }
