"""
Time navigation logic for date range calculations.

Pure functions for computing time periods, navigating between them,
and formatting descriptions. Completely decoupled from UI and state.
All functions fully typed and testable.
"""

import calendar
from datetime import date
from typing import Literal, NamedTuple

from dateutil.relativedelta import relativedelta

PeriodType = Literal["year", "month"]


class DateRange(NamedTuple):
    """A date range with start and end dates."""

    start_date: date
    end_date: date
    description: str


class TimeNavigator:
    """
    Handles time period calculations and navigation.

    All methods are static/pure functions with no side effects.
    Fully testable without any UI dependencies.
    """

    @staticmethod
    def get_month_range(year: int, month: int) -> DateRange:
        """
        Get first and last day of a specific month.

        Args:
            year: Year (e.g., 2025)
            month: Month number (1-12)

        Returns:
            DateRange with start, end, and description

        Raises:
            ValueError: If month is not 1-12

        Examples:
            >>> range = TimeNavigator.get_month_range(2025, 1)
            >>> range.start_date
            datetime.date(2025, 1, 1)
            >>> range.end_date
            datetime.date(2025, 1, 31)
            >>> range.description
            'January 2025'
        """
        if not 1 <= month <= 12:
            raise ValueError(f"Month must be 1-12, got {month}")

        first_day = date(year, month, 1)
        last_day_num = calendar.monthrange(year, month)[1]
        last_day = date(year, month, last_day_num)

        # Format month name
        month_name = date(year, month, 1).strftime("%B")
        description = f"{month_name} {year}"

        return DateRange(start_date=first_day, end_date=last_day, description=description)

    @staticmethod
    def get_year_range(year: int) -> DateRange:
        """
        Get first and last day of a year.

        Args:
            year: Year (e.g., 2025)

        Returns:
            DateRange for the full year

        Examples:
            >>> range = TimeNavigator.get_year_range(2025)
            >>> range.start_date
            datetime.date(2025, 1, 1)
            >>> range.end_date
            datetime.date(2025, 12, 31)
            >>> range.description
            'Year 2025'
        """
        return DateRange(
            start_date=date(year, 1, 1),
            end_date=date(year, 12, 31),
            description=f"Year {year}",
        )

    @staticmethod
    def get_current_year_range() -> DateRange:
        """
        Get date range for current year.

        Returns:
            DateRange for current year

        Examples:
            >>> from datetime import date
            >>> range = TimeNavigator.get_current_year_range()
            >>> range.start_date.year == date.today().year
            True
        """
        today = date.today()
        return TimeNavigator.get_year_range(today.year)

    @staticmethod
    def get_current_month_range() -> DateRange:
        """
        Get date range for current month.

        Returns:
            DateRange for current month

        Examples:
            >>> from datetime import date
            >>> range = TimeNavigator.get_current_month_range()
            >>> today = date.today()
            >>> range.start_date.month == today.month
            True
        """
        today = date.today()
        return TimeNavigator.get_month_range(today.year, today.month)

    @staticmethod
    def is_full_year_range(start_date: date, end_date: date) -> bool:
        """
        Check if a date range represents a full calendar year.

        Args:
            start_date: Range start date
            end_date: Range end date

        Returns:
            True if range is Jan 1 - Dec 31 of same year

        Examples:
            >>> TimeNavigator.is_full_year_range(
            ...     date(2025, 1, 1), date(2025, 12, 31)
            ... )
            True
            >>> TimeNavigator.is_full_year_range(
            ...     date(2025, 1, 1), date(2025, 6, 30)
            ... )
            False
        """
        return (
            start_date.month == 1
            and start_date.day == 1
            and end_date.month == 12
            and end_date.day == 31
            and start_date.year == end_date.year
        )

    @staticmethod
    def is_full_month_range(start_date: date, end_date: date) -> bool:
        """
        Check if a date range represents a full calendar month.

        Args:
            start_date: Range start date
            end_date: Range end date

        Returns:
            True if range is first to last day of a month

        Examples:
            >>> TimeNavigator.is_full_month_range(
            ...     date(2025, 1, 1), date(2025, 1, 31)
            ... )
            True
            >>> TimeNavigator.is_full_month_range(
            ...     date(2025, 2, 1), date(2025, 2, 28)
            ... )
            True
        """
        # Check if start is first day
        if start_date.day != 1:
            return False

        # Check if end is last day of same month
        last_day = calendar.monthrange(start_date.year, start_date.month)[1]
        return (
            end_date.year == start_date.year
            and end_date.month == start_date.month
            and end_date.day == last_day
        )

    @staticmethod
    def previous_period(start_date: date, end_date: date) -> DateRange:
        """
        Navigate to previous time period.

        Preserves granularity: year->year, month->month.

        Args:
            start_date: Current range start
            end_date: Current range end

        Returns:
            DateRange for previous period

        Examples:
            >>> # Previous year
            >>> range = TimeNavigator.previous_period(
            ...     date(2025, 1, 1), date(2025, 12, 31)
            ... )
            >>> range.start_date
            datetime.date(2024, 1, 1)
            >>> range.description
            'Year 2024'

            >>> # Previous month
            >>> range = TimeNavigator.previous_period(
            ...     date(2025, 3, 1), date(2025, 3, 31)
            ... )
            >>> range.start_date
            datetime.date(2025, 2, 1)
            >>> range.description
            'February 2025'
        """
        if TimeNavigator.is_full_year_range(start_date, end_date):
            # Navigate to previous year
            new_year = start_date.year - 1
            return TimeNavigator.get_year_range(new_year)
        else:
            # Navigate to previous month
            prev_month_start = start_date.replace(day=1) - relativedelta(months=1)
            return TimeNavigator.get_month_range(prev_month_start.year, prev_month_start.month)

    @staticmethod
    def next_period(start_date: date, end_date: date) -> DateRange:
        """
        Navigate to next time period.

        Preserves granularity: year->year, month->month.

        Args:
            start_date: Current range start
            end_date: Current range end

        Returns:
            DateRange for next period

        Examples:
            >>> # Next year
            >>> range = TimeNavigator.next_period(
            ...     date(2025, 1, 1), date(2025, 12, 31)
            ... )
            >>> range.start_date
            datetime.date(2026, 1, 1)

            >>> # Next month
            >>> range = TimeNavigator.next_period(
            ...     date(2025, 1, 1), date(2025, 1, 31)
            ... )
            >>> range.start_date
            datetime.date(2025, 2, 1)
        """
        if TimeNavigator.is_full_year_range(start_date, end_date):
            # Navigate to next year
            new_year = start_date.year + 1
            return TimeNavigator.get_year_range(new_year)
        else:
            # Navigate to next month
            next_month_start = start_date.replace(day=1) + relativedelta(months=1)
            return TimeNavigator.get_month_range(next_month_start.year, next_month_start.month)

    @staticmethod
    def get_month_name(month: int) -> str:
        """
        Get month name from number.

        Args:
            month: Month number (1-12)

        Returns:
            Month name

        Raises:
            ValueError: If month not 1-12

        Examples:
            >>> TimeNavigator.get_month_name(1)
            'January'
            >>> TimeNavigator.get_month_name(12)
            'December'
        """
        if not 1 <= month <= 12:
            raise ValueError(f"Month must be 1-12, got {month}")

        return date(2000, month, 1).strftime("%B")  # Year doesn't matter for name
