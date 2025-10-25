"""
Centralized category definitions for moneyflow.

This module provides Monarch Money's default category structure and supports
custom categories via ~/.moneyflow/categories.yaml configuration.

The category system supports:
- Default Monarch Money categories and groups
- Custom categories added to existing groups
- Custom category groups
- Renaming categories to match your Monarch account
- Moving categories between groups
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

logger = logging.getLogger(__name__)

# Monarch Money default category groups
# These are the standard categories that come with every Monarch Money account
# Source: Monarch Money defaults (as of 2025-01)
#
# Each group includes a top-level category with the same name for items that don't
# fit exactly into subcategories (e.g., "Business" category in Business group)
DEFAULT_CATEGORY_GROUPS: Dict[str, List[str]] = {
    "Income": [
        "Income",
        "Paychecks",
        "Interest",
        "Business Income",
        "Other Income",
    ],
    "Gifts & Donations": [
        "Gifts & Donations",
        "Charity",
        "Gifts",
    ],
    "Auto & Transport": [
        "Auto & Transport",
        "Auto Payment",
        "Public Transit",
        "Gas",
        "Auto Maintenance",
        "Parking & Tolls",
        "Taxi & Ride Shares",
    ],
    "Housing": [
        "Housing",
        "Mortgage",
        "Rent",
        "Home Improvement",
    ],
    "Bills & Utilities": [
        "Bills & Utilities",
        "Garbage",
        "Water",
        "Gas & Electric",
        "Internet & Cable",
        "Phone",
    ],
    "Food & Dining": [
        "Food & Dining",
        "Groceries",
        "Restaurants & Bars",
        "Coffee Shops",
    ],
    "Travel & Lifestyle": [
        "Travel & Lifestyle",
        "Travel & Vacation",
        "Entertainment & Recreation",
        "Personal",
        "Pets",
        "Fun Money",
    ],
    "Shopping": [
        "Shopping",
        "Clothing",
        "Furniture & Housewares",
        "Electronics",
    ],
    "Children": [
        "Children",
        "Child Care",
        "Child Activities",
    ],
    "Education": [
        "Education",
        "Student Loans",
    ],
    "Health & Wellness": [
        "Health & Wellness",
        "Medical",
        "Dentist",
        "Fitness",
    ],
    "Financial": [
        "Financial",
        "Loan Repayment",
        "Financial & Legal Services",
        "Financial Fees",
        "Cash & ATM",
        "Insurance",
        "Taxes",
    ],
    "Other": [
        "Other",
        "Uncategorized",
        "Check",
        "Miscellaneous",
    ],
    "Business": [
        "Business",
        "Advertising & Promotion",
        "Business Utilities & Communication",
        "Employee Wages & Contract Labor",
        "Business Travel & Meals",
        "Business Auto Expenses",
        "Business Insurance",
        "Office Supplies & Expenses",
        "Office Rent",
        "Postage & Shipping",
    ],
    "Transfers": [
        "Transfers",
        "Transfer",
        "Credit Card Payment",
        "Balance Adjustments",
    ],
}


def load_custom_categories(config_dir: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Load custom category configuration from ~/.moneyflow/categories.yaml.

    Args:
        config_dir: Optional custom config directory (default: ~/.moneyflow)

    Returns:
        Dict with custom category config or None if file doesn't exist

    YAML Format:
        version: 1
        rename_groups:
          "Old Group Name": "New Group Name"
        rename_categories:
          "Old Category Name": "New Category Name"
        add_to_groups:
          GroupName:
            - Category 1
            - Category 2
        custom_groups:
          CustomGroup:
            - Category A
        move_categories:
          "Category Name": "New Group"
    """
    if config_dir is None:
        config_dir = str(Path.home() / ".moneyflow")

    config_path = Path(config_dir) / "categories.yaml"

    if not config_path.exists():
        logger.debug(f"No custom categories file at {config_path}")
        return None

    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        if not config:
            logger.warning(f"Empty categories config at {config_path}")
            return None

        # Validate version
        version = config.get("version")
        if version != 1:
            logger.warning(f"Unsupported categories.yaml version: {version} (expected 1)")
            return None

        logger.info(f"Loaded custom categories from {config_path}")
        return config

    except yaml.YAMLError as e:
        logger.error(f"Failed to parse {config_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to load custom categories: {e}")
        return None


def merge_category_groups(
    defaults: Dict[str, List[str]], custom_config: Optional[Dict[str, Any]]
) -> Dict[str, List[str]]:
    """
    Merge custom category configuration with defaults.

    Process order:
    1. Start with defaults
    2. Apply group renames (rename_groups)
    3. Apply category renames (rename_categories)
    4. Add custom categories to existing groups (add_to_groups)
    5. Add entirely new custom groups (custom_groups)
    6. Move categories between groups (move_categories)

    Args:
        defaults: Default category groups dict
        custom_config: Custom configuration from YAML (or None)

    Returns:
        Merged category groups dict
    """
    import copy

    if not custom_config:
        return defaults

    # Deep copy to avoid mutating defaults
    merged = copy.deepcopy(defaults)

    # Step 1: Apply group renames (rename entire groups)
    group_renames = custom_config.get("rename_groups", {})
    if group_renames:
        for old_name, new_name in group_renames.items():
            if old_name in merged:
                merged[new_name] = merged.pop(old_name)
                logger.info(f"Renamed group: '{old_name}' → '{new_name}'")
            else:
                logger.warning(f"Cannot rename non-existent group: '{old_name}'")

    # Step 2: Apply category renames (rename categories in-place)
    category_renames = custom_config.get("rename_categories", {})
    if category_renames:
        for group_name, categories in merged.items():
            merged[group_name] = [category_renames.get(cat, cat) for cat in categories]
        logger.info(f"Applied {len(category_renames)} category renames")

    # Step 3: Add custom categories to existing groups
    add_to_groups = custom_config.get("add_to_groups", {})
    for group_name, new_categories in add_to_groups.items():
        if group_name in merged:
            # Add to existing group (avoid duplicates)
            for cat in new_categories:
                if cat not in merged[group_name]:
                    merged[group_name].append(cat)
            logger.info(f"Added {len(new_categories)} categories to {group_name}")
        else:
            logger.warning(f"Cannot add to non-existent group: {group_name}")

    # Step 4: Add custom groups
    custom_groups = custom_config.get("custom_groups", {})
    for group_name, categories in custom_groups.items():
        if group_name in merged:
            logger.warning(f"Custom group '{group_name}' already exists, skipping")
        else:
            merged[group_name] = list(categories)
            logger.info(f"Added custom group: {group_name} with {len(categories)} categories")

    # Step 5: Move categories between groups
    moves = custom_config.get("move_categories", {})
    for category_name, new_group in moves.items():
        # Check if destination group exists first
        if new_group not in merged:
            logger.warning(f"Cannot move '{category_name}' to non-existent group: {new_group}")
            continue

        # Remove from old group
        old_group_name = None
        for group_name, categories in merged.items():
            if category_name in categories:
                categories.remove(category_name)
                old_group_name = group_name
                logger.debug(f"Removed '{category_name}' from {group_name}")
                break

        # Add to new group
        if category_name not in merged[new_group]:
            merged[new_group].append(category_name)
        logger.info(f"Moved '{category_name}' from {old_group_name} to {new_group}")

    return merged


def build_category_to_group_mapping(category_groups: Dict[str, List[str]]) -> Dict[str, str]:
    """
    Build reverse mapping from category name to group name.

    Args:
        category_groups: Dict mapping group_name → [category_names]

    Returns:
        Dict mapping category_name → group_name
    """
    category_to_group = {}
    for group_name, categories in category_groups.items():
        for category in categories:
            category_to_group[category] = group_name
    return category_to_group


def get_effective_category_groups(config_dir: Optional[str] = None) -> Dict[str, List[str]]:
    """
    Get effective category groups (defaults merged with custom config).

    This is the main entry point for getting category groups.
    It loads custom categories from ~/.moneyflow/categories.yaml and merges
    them with Monarch defaults.

    Args:
        config_dir: Optional custom config directory (default: ~/.moneyflow)

    Returns:
        Merged category groups dict
    """
    custom_config = load_custom_categories(config_dir)
    return merge_category_groups(DEFAULT_CATEGORY_GROUPS, custom_config)


# Deprecated: Old STANDARD_CATEGORIES format (kept for backwards compatibility)
# Use get_effective_category_groups() instead
STANDARD_CATEGORIES: List[Tuple[str, str, str]] = [
    # Business
    ("cat_accounting", "Accounting", "Business"),
    ("cat_business", "Business", "Business"),
    ("cat_office_rent", "Office Rent", "Business"),
    ("cat_business_electronics", "Business Electronics", "Business"),
    ("cat_business_software", "Business Software", "Business"),
    ("cat_business_travel_meals", "Business Travel & Meals", "Business"),
    ("cat_business_utilities", "Business Utilities & Communication", "Business"),
    ("cat_office_supplies", "Office Supplies", "Business"),
    ("cat_office_expenses", "Office Supplies & Expenses", "Business"),
    ("cat_postage", "Postage & Shipping", "Business"),
    ("cat_contracting", "Employee Wages & Contract Labor", "Business"),
    ("cat_business_auto", "Business Auto Expenses", "Business"),
    ("cat_advertising", "Advertising & Promotion", "Business"),
    # Cash & ATM
    ("cat_cash", "Cash & ATM", "Cash & ATM"),
    ("cat_atm", "ATM", "Cash & ATM"),
    ("cat_check", "Check", "Cash & ATM"),
    # Food & Dining
    ("cat_food_dining", "Food & Dining", "Food & Dining"),
    ("cat_restaurants", "Restaurants & Bars", "Food & Dining"),
    ("cat_coffee", "Coffee Shops", "Food & Dining"),
    ("cat_groceries", "Groceries", "Food & Dining"),
    ("cat_fast_food", "Fast Food", "Food & Dining"),
    ("cat_food_drink", "Food & Drink", "Food & Dining"),
    ("cat_alcohol", "Alcohol", "Food & Dining"),
    ("cat_quick_eats", "Quick Eats", "Food & Dining"),
    # Travel
    ("cat_airfare", "Airfare", "Travel"),
    ("cat_auto_rental", "Auto Rental", "Travel"),
    ("cat_hotel", "Hotel", "Travel"),
    ("cat_trains", "Trains", "Travel"),
    ("cat_public_transit", "Public Transit", "Travel"),
    ("cat_taxi", "Taxi & Ride Shares", "Travel"),
    ("cat_luggage", "Luggage", "Travel"),
    ("cat_travel_services", "Travel Services", "Travel"),
    ("cat_travel_vacation", "Travel & Vacation", "Travel"),
    # Auto & Transport
    ("cat_auto_transport", "Auto & Transport", "Auto & Transport"),
    ("cat_gas", "Gas", "Auto & Transport"),
    ("cat_parking_tolls", "Parking & Tolls", "Auto & Transport"),
    ("cat_auto_insurance", "Auto Insurance", "Auto & Transport"),
    ("cat_auto_payment", "Auto Payment", "Auto & Transport"),
    ("cat_auto_maintenance", "Auto Maintenance", "Auto & Transport"),
    # Services
    ("cat_internet_cable", "Internet & Cable", "Services"),
    ("cat_streaming", "Streaming", "Services"),
    ("cat_laundry", "Laundry & Dry Cleaning", "Services"),
    ("cat_home_services", "Home Services", "Services"),
    ("cat_software", "Software", "Services"),
    ("cat_childcare", "Child Care", "Services"),
    # Housing
    ("cat_housing", "Housing", "Housing"),
    ("cat_gas_electric", "Gas & Electric", "Housing"),
    ("cat_mortgage", "Mortgage", "Housing"),
    ("cat_rent", "Rent", "Housing"),
    ("cat_home_improvement", "Home Improvement", "Housing"),
    ("cat_water", "Water", "Housing"),
    ("cat_garbage", "Garbage", "Housing"),
    # Shopping
    ("cat_shopping", "Shopping", "Shopping"),
    ("cat_child_stuff", "Child Stuff", "Shopping"),
    ("cat_clothing", "Clothing", "Shopping"),
    ("cat_electronics", "Electronics", "Shopping"),
    ("cat_home_supplies", "Home Supplies", "Shopping"),
    ("cat_kitchen", "Kitchen", "Shopping"),
    ("cat_furniture", "Furniture & Housewares", "Shopping"),
    ("cat_jewelry", "Jewelry & Accessories", "Shopping"),
    ("cat_video_games", "Video Games", "Shopping"),
    ("cat_hobbies", "Hobbies", "Shopping"),
    ("cat_books", "Books", "Shopping"),
    ("cat_membership", "Membership", "Shopping"),
    # Entertainment
    ("cat_entertainment_rec", "Entertainment & Recreation", "Entertainment"),
    ("cat_entertainment", "Entertainment", "Entertainment"),
    # Education
    ("cat_education", "Education", "Education"),
    # Health & Fitness
    ("cat_medical", "Medical", "Health & Fitness"),
    ("cat_dentist", "Dentist", "Health & Fitness"),
    ("cat_fitness", "Fitness", "Health & Fitness"),
    ("cat_pets", "Pets", "Health & Fitness"),
    ("cat_pharmacy", "Pharmacy", "Health & Fitness"),
    ("cat_eyecare", "Eyecare", "Health & Fitness"),
    ("cat_hearing", "Hearing", "Health & Fitness"),
    ("cat_supplements", "Supplements", "Health & Fitness"),
    ("cat_workout_classes", "Workout Classes", "Health & Fitness"),
    ("cat_health_wellness", "Health & Wellness", "Health & Fitness"),
    # Gifts & Charity
    ("cat_gifts_charity", "Gifts & Charity", "Gifts & Charity"),
    ("cat_gifts", "Gifts", "Gifts & Charity"),
    ("cat_charity", "Charity", "Gifts & Charity"),
    # Bills & Utilities
    ("cat_phone", "Phone", "Bills & Utilities"),
    # Financial
    ("cat_bank_fees", "Bank Fees", "Financial"),
    ("cat_financial_legal", "Financial & Legal Services", "Financial"),
    ("cat_financial_fees", "Financial Fees", "Financial"),
    ("cat_insurance", "Insurance", "Financial"),
    ("cat_life_insurance", "Life Insurance", "Financial"),
    ("cat_loan_repayment", "Loan Repayment", "Financial"),
    ("cat_student_loans", "Student Loans", "Financial"),
    ("cat_taxes", "Taxes", "Financial"),
    # Personal Care
    ("cat_chiropractic", "Chiropractic & Massage", "Personal Care"),
    ("cat_hair", "Hair", "Personal Care"),
    ("cat_personal_care", "Personal Care", "Personal Care"),
    # Income
    ("cat_paychecks", "Paychecks", "Income"),
    ("cat_interest", "Interest", "Income"),
    ("cat_business_income", "Business Income", "Income"),
    ("cat_other_income", "Other Income", "Income"),
    # Transfers
    ("cat_transfer", "Transfer", "Transfers"),
    ("cat_credit_payment", "Credit Card Payment", "Transfers"),
    ("cat_balance_adj", "Balance Adjustments", "Transfers"),
    # Uncategorized
    ("cat_uncategorized", "Uncategorized", "Uncategorized"),
    ("cat_check", "Check", "Uncategorized"),
    ("cat_miscellaneous", "Miscellaneous", "Uncategorized"),
]


def get_category_groups() -> List[Tuple[str, str]]:
    """
    Get all unique category groups from standard categories.

    Returns:
        List of (group_name, group_name) tuples
        (using same value for id and name since we don't have separate group IDs)
    """
    groups = set()
    for _, _, group_name in STANDARD_CATEGORIES:
        groups.add(group_name)

    return sorted([(g, g) for g in groups])


def get_category_by_id(category_id: str) -> Tuple[str, str, str]:
    """
    Look up a category by ID.

    Args:
        category_id: Category ID to look up

    Returns:
        Tuple of (id, name, group_name)

    Raises:
        KeyError: If category_id not found
    """
    for cat in STANDARD_CATEGORIES:
        if cat[0] == category_id:
            return cat
    raise KeyError(f"Category not found: {category_id}")


def get_category_by_name(category_name: str) -> Tuple[str, str, str]:
    """
    Look up a category by name.

    Args:
        category_name: Category name to look up

    Returns:
        Tuple of (id, name, group_name)

    Raises:
        KeyError: If category_name not found
    """
    for cat in STANDARD_CATEGORIES:
        if cat[1].lower() == category_name.lower():
            return cat
    raise KeyError(f"Category not found: {category_name}")
