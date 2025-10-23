"""
Centralized category definitions for moneyflow.

This module provides a standard set of transaction categories that all backends
can use. Categories are backend-agnostic and follow common personal finance
organization patterns.

Future: Support custom categories via config file (~/.moneyflow/categories.yaml)
"""

from typing import List, Tuple

# Standard categories as (id, name, group_name) tuples
# These match the categories from Monarch Money (from CATEGORY_GROUPS in data_manager.py)
# Organized by group for easy reference
STANDARD_CATEGORIES: List[Tuple[str, str, str]] = [
    # Business
    ("cat_accounting", "Accounting", "Business"),
    ("cat_business", "Business", "Business"),
    ("cat_office_rent", "Office Rent", "Business"),
    ("cat_business_electronics", "Business Electronics", "Business"),
    ("cat_business_software", "Business Software", "Business"),
    ("cat_business_utilities", "Business Utilities & Communication", "Business"),
    ("cat_office_supplies", "Office Supplies", "Business"),
    ("cat_office_expenses", "Office Supplies & Expenses", "Business"),
    ("cat_postage", "Postage & Shipping", "Business"),

    # Cash & ATM
    ("cat_cash", "Cash & ATM", "Cash & ATM"),
    ("cat_atm", "ATM", "Cash & ATM"),

    # Food & Dining
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

    # Automotive
    ("cat_gas", "Gas", "Automotive"),
    ("cat_parking_tolls", "Parking & Tolls", "Automotive"),
    ("cat_auto_payment", "Auto Payment", "Automotive"),
    ("cat_auto_maintenance", "Auto Maintenance", "Automotive"),

    # Services
    ("cat_internet_cable", "Internet & Cable", "Services"),
    ("cat_streaming", "Streaming", "Services"),
    ("cat_laundry", "Laundry & Dry Cleaning", "Services"),
    ("cat_home_services", "Home Services", "Services"),
    ("cat_software", "Software", "Services"),
    ("cat_childcare", "Child Care", "Services"),

    # Housing
    ("cat_gas_electric", "Gas & Electric", "Housing"),
    ("cat_mortgage", "Mortgage", "Housing"),
    ("cat_rent", "Rent", "Housing"),
    ("cat_home_improvement", "Home Improvement", "Housing"),
    ("cat_water", "Water", "Housing"),
    ("cat_garbage", "Garbage", "Housing"),

    # Shopping
    ("cat_shopping", "Shopping", "Shopping"),
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
    ("cat_entertainment", "Entertainment & Recreation", "Entertainment"),

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
    ("cat_gifts", "Gifts", "Gifts & Charity"),
    ("cat_charity", "Charity", "Gifts & Charity"),

    # Bills & Utilities
    ("cat_phone", "Phone", "Bills & Utilities"),
    ("cat_insurance", "Insurance", "Bills & Utilities"),

    # Financial
    ("cat_financial_legal", "Financial & Legal Services", "Financial"),
    ("cat_financial_fees", "Financial Fees", "Financial"),
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
