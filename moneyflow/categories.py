"""
Centralized category definitions for moneyflow.

This module provides a standard set of transaction categories that all backends
can use. Categories are backend-agnostic and follow common personal finance
organization patterns.

Future: Support custom categories via config file (~/.moneyflow/categories.yaml)
"""

from typing import List, Tuple

# Standard categories as (id, name, group_name) tuples
# These are common categories used across personal finance tracking
STANDARD_CATEGORIES: List[Tuple[str, str, str]] = [
    # Food & Dining
    ("cat_groceries", "Groceries", "Food & Dining"),
    ("cat_restaurants", "Restaurants & Dining", "Food & Dining"),
    ("cat_coffee", "Coffee Shops", "Food & Dining"),
    ("cat_fast_food", "Fast Food", "Food & Dining"),
    ("cat_alcohol", "Alcohol & Bars", "Food & Dining"),

    # Shopping
    ("cat_shopping", "Shopping", "Shopping"),
    ("cat_clothing", "Clothing", "Shopping"),
    ("cat_electronics", "Electronics", "Shopping"),
    ("cat_software", "Software", "Shopping"),
    ("cat_books", "Books", "Shopping"),
    ("cat_hobbies", "Hobbies", "Shopping"),
    ("cat_sporting_goods", "Sporting Goods", "Shopping"),

    # Transportation
    ("cat_gas", "Gas & Fuel", "Transportation"),
    ("cat_parking", "Parking", "Transportation"),
    ("cat_public_transit", "Public Transportation", "Transportation"),
    ("cat_auto_service", "Service & Parts", "Transportation"),
    ("cat_auto_payment", "Auto Payment", "Transportation"),
    ("cat_auto_insurance", "Auto Insurance", "Transportation"),

    # Home
    ("cat_rent", "Rent", "Home"),
    ("cat_mortgage", "Mortgage", "Home"),
    ("cat_home_improvement", "Home Improvement", "Home"),
    ("cat_furniture", "Furniture", "Home"),
    ("cat_household_supplies", "Household Supplies", "Home"),
    ("cat_lawn_garden", "Lawn & Garden", "Home"),

    # Bills & Utilities
    ("cat_phone", "Mobile Phone", "Bills & Utilities"),
    ("cat_internet", "Internet", "Bills & Utilities"),
    ("cat_utilities", "Utilities", "Bills & Utilities"),
    ("cat_cable", "Cable", "Bills & Utilities"),
    ("cat_streaming", "Streaming Services", "Bills & Utilities"),

    # Health & Fitness
    ("cat_pharmacy", "Pharmacy", "Health & Fitness"),
    ("cat_fitness", "Gym", "Health & Fitness"),
    ("cat_health", "Doctor", "Health & Fitness"),
    ("cat_dentist", "Dentist", "Health & Fitness"),
    ("cat_health_insurance", "Health Insurance", "Health & Fitness"),

    # Entertainment
    ("cat_entertainment", "Entertainment", "Entertainment"),
    ("cat_movies", "Movies & DVDs", "Entertainment"),
    ("cat_music", "Music", "Entertainment"),
    ("cat_games", "Video Games", "Entertainment"),
    ("cat_concerts", "Concerts & Events", "Entertainment"),

    # Personal Care
    ("cat_personal_care", "Personal Care", "Personal Care"),
    ("cat_hair", "Hair", "Personal Care"),
    ("cat_spa", "Spa & Massage", "Personal Care"),

    # Pets
    ("cat_pet_food", "Pet Food & Supplies", "Pets"),
    ("cat_veterinary", "Veterinary", "Pets"),

    # Kids
    ("cat_baby_supplies", "Baby Supplies", "Kids"),
    ("cat_toys", "Toys", "Kids"),
    ("cat_childcare", "Childcare", "Kids"),
    ("cat_kids_activities", "Kids Activities", "Kids"),

    # Education
    ("cat_tuition", "Tuition", "Education"),
    ("cat_books_education", "Books & Supplies", "Education"),

    # Travel
    ("cat_hotels", "Hotels", "Travel"),
    ("cat_airfare", "Airfare", "Travel"),
    ("cat_vacation", "Vacation", "Travel"),

    # Gifts & Donations
    ("cat_gifts", "Gifts", "Gifts & Donations"),
    ("cat_charity", "Charity", "Gifts & Donations"),

    # Financial
    ("cat_atm", "ATM Fee", "Fees & Charges"),
    ("cat_bank_fee", "Bank Fee", "Fees & Charges"),
    ("cat_late_fee", "Late Fee", "Fees & Charges"),

    # Income
    ("cat_paycheck", "Paycheck", "Income"),
    ("cat_bonus", "Bonus", "Income"),
    ("cat_investment_income", "Investment Income", "Income"),

    # Transfers
    ("cat_transfer", "Transfer", "Transfers"),
    ("cat_credit_payment", "Credit Card Payment", "Transfers"),

    # Uncategorized (default)
    ("cat_uncategorized", "Uncategorized", "Uncategorized"),
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
