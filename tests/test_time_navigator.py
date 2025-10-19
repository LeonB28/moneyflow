"""
Tests for time_navigator module.

Comprehensive tests for date range calculations, period navigation,
and edge cases like leap years and year boundaries.
"""

import calendar
from datetime import date

import pytest

from moneyflow.time_navigator import TimeNavigator


class TestGetMonthRange:
    """Tests for get_month_range method."""

    def test_january_range(self):
        """Should return correct range for January."""
        range_obj = TimeNavigator.get_month_range(2025, 1)

        assert range_obj.start_date == date(2025, 1, 1)
        assert range_obj.end_date == date(2025, 1, 31)
        assert range_obj.description == "January 2025"

    def test_february_non_leap_year(self):
        """Should return 28 days for February in non-leap year."""
        range_obj = TimeNavigator.get_month_range(2025, 2)

        assert range_obj.start_date == date(2025, 2, 1)
        assert range_obj.end_date == date(2025, 2, 28)
        assert range_obj.description == "February 2025"

    def test_february_leap_year(self):
        """Should return 29 days for February in leap year."""
        range_obj = TimeNavigator.get_month_range(2024, 2)

        assert range_obj.start_date == date(2024, 2, 1)
        assert range_obj.end_date == date(2024, 2, 29)
        assert range_obj.description == "February 2024"

    def test_december_range(self):
        """Should return correct range for December."""
        range_obj = TimeNavigator.get_month_range(2025, 12)

        assert range_obj.start_date == date(2025, 12, 1)
        assert range_obj.end_date == date(2025, 12, 31)
        assert range_obj.description == "December 2025"

    def test_april_has_30_days(self):
        """Should return 30 days for April."""
        range_obj = TimeNavigator.get_month_range(2025, 4)

        assert range_obj.end_date == date(2025, 4, 30)

    def test_invalid_month_zero(self):
        """Should raise ValueError for month 0."""
        with pytest.raises(ValueError, match="Month must be 1-12"):
            TimeNavigator.get_month_range(2025, 0)

    def test_invalid_month_thirteen(self):
        """Should raise ValueError for month 13."""
        with pytest.raises(ValueError, match="Month must be 1-12"):
            TimeNavigator.get_month_range(2025, 13)

    def test_all_months_valid(self):
        """Should return valid ranges for all 12 months."""
        month_names = [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]
        for month, expected_name in enumerate(month_names, 1):
            range_obj = TimeNavigator.get_month_range(2025, month)
            assert range_obj.start_date.month == month
            assert range_obj.end_date.month == month
            assert expected_name in range_obj.description  # Should have month name


class TestGetYearRange:
    """Tests for get_year_range method."""

    def test_full_year_2025(self):
        """Should return Jan 1 - Dec 31 for 2025."""
        range_obj = TimeNavigator.get_year_range(2025)

        assert range_obj.start_date == date(2025, 1, 1)
        assert range_obj.end_date == date(2025, 12, 31)
        assert range_obj.description == "Year 2025"

    def test_leap_year_2024(self):
        """Should return full year for leap year."""
        range_obj = TimeNavigator.get_year_range(2024)

        assert range_obj.start_date == date(2024, 1, 1)
        assert range_obj.end_date == date(2024, 12, 31)

    def test_year_2000(self):
        """Should handle year 2000."""
        range_obj = TimeNavigator.get_year_range(2000)

        assert range_obj.start_date == date(2000, 1, 1)
        assert range_obj.end_date == date(2000, 12, 31)


class TestCurrentPeriods:
    """Tests for get_current_* methods."""

    def test_current_year_range(self):
        """Should return current year range."""
        range_obj = TimeNavigator.get_current_year_range()
        today = date.today()

        assert range_obj.start_date.year == today.year
        assert range_obj.end_date.year == today.year
        assert range_obj.start_date == date(today.year, 1, 1)
        assert range_obj.end_date == date(today.year, 12, 31)

    def test_current_month_range(self):
        """Should return current month range."""
        range_obj = TimeNavigator.get_current_month_range()
        today = date.today()

        assert range_obj.start_date.year == today.year
        assert range_obj.start_date.month == today.month
        assert range_obj.start_date.day == 1

        # Check end date is last day of current month
        last_day = calendar.monthrange(today.year, today.month)[1]
        assert range_obj.end_date.day == last_day


class TestIsFullYearRange:
    """Tests for is_full_year_range method."""

    def test_full_year_2025(self):
        """Should return True for Jan 1 - Dec 31."""
        assert TimeNavigator.is_full_year_range(date(2025, 1, 1), date(2025, 12, 31)) is True

    def test_leap_year_2024(self):
        """Should return True for full leap year."""
        assert TimeNavigator.is_full_year_range(date(2024, 1, 1), date(2024, 12, 31)) is True

    def test_partial_year_jan_to_june(self):
        """Should return False for partial year."""
        assert TimeNavigator.is_full_year_range(date(2025, 1, 1), date(2025, 6, 30)) is False

    def test_full_year_wrong_start_month(self):
        """Should return False if not starting in January."""
        assert TimeNavigator.is_full_year_range(date(2025, 2, 1), date(2025, 12, 31)) is False

    def test_full_year_wrong_end_month(self):
        """Should return False if not ending in December."""
        assert TimeNavigator.is_full_year_range(date(2025, 1, 1), date(2025, 11, 30)) is False

    def test_crosses_year_boundary(self):
        """Should return False for range crossing year boundary."""
        assert TimeNavigator.is_full_year_range(date(2024, 1, 1), date(2025, 12, 31)) is False


class TestIsFullMonthRange:
    """Tests for is_full_month_range method."""

    def test_full_month_january(self):
        """Should return True for full January."""
        assert TimeNavigator.is_full_month_range(date(2025, 1, 1), date(2025, 1, 31)) is True

    def test_full_month_february_non_leap(self):
        """Should return True for full February (28 days)."""
        assert TimeNavigator.is_full_month_range(date(2025, 2, 1), date(2025, 2, 28)) is True

    def test_full_month_february_leap_year(self):
        """Should return True for full February in leap year (29 days)."""
        assert TimeNavigator.is_full_month_range(date(2024, 2, 1), date(2024, 2, 29)) is True

    def test_partial_month_mid_to_end(self):
        """Should return False for partial month."""
        assert TimeNavigator.is_full_month_range(date(2025, 1, 15), date(2025, 1, 31)) is False

    def test_partial_month_start_to_mid(self):
        """Should return False when not ending on last day."""
        assert TimeNavigator.is_full_month_range(date(2025, 1, 1), date(2025, 1, 15)) is False

    def test_crosses_month_boundary(self):
        """Should return False for range crossing months."""
        assert TimeNavigator.is_full_month_range(date(2025, 1, 1), date(2025, 2, 28)) is False


class TestPreviousPeriod:
    """Tests for previous_period method."""

    def test_previous_year_from_full_year(self):
        """Should navigate to previous year when viewing full year."""
        range_obj = TimeNavigator.previous_period(date(2025, 1, 1), date(2025, 12, 31))

        assert range_obj.start_date == date(2024, 1, 1)
        assert range_obj.end_date == date(2024, 12, 31)
        assert range_obj.description == "Year 2024"

    def test_previous_month_from_full_month(self):
        """Should navigate to previous month when viewing full month."""
        range_obj = TimeNavigator.previous_period(date(2025, 3, 1), date(2025, 3, 31))

        assert range_obj.start_date == date(2025, 2, 1)
        assert range_obj.end_date == date(2025, 2, 28)
        assert range_obj.description == "February 2025"

    def test_previous_month_across_year_boundary(self):
        """Should navigate from January to December of previous year."""
        range_obj = TimeNavigator.previous_period(date(2025, 1, 1), date(2025, 1, 31))

        assert range_obj.start_date == date(2024, 12, 1)
        assert range_obj.end_date == date(2024, 12, 31)
        assert range_obj.description == "December 2024"

    def test_previous_month_from_march_to_february_leap_year(self):
        """Should handle leap year February correctly."""
        range_obj = TimeNavigator.previous_period(date(2024, 3, 1), date(2024, 3, 31))

        assert range_obj.end_date == date(2024, 2, 29)  # Leap year

    def test_previous_month_from_march_to_february_non_leap(self):
        """Should handle non-leap year February correctly."""
        range_obj = TimeNavigator.previous_period(date(2025, 3, 1), date(2025, 3, 31))

        assert range_obj.end_date == date(2025, 2, 28)  # Non-leap year


class TestNextPeriod:
    """Tests for next_period method."""

    def test_next_year_from_full_year(self):
        """Should navigate to next year when viewing full year."""
        range_obj = TimeNavigator.next_period(date(2025, 1, 1), date(2025, 12, 31))

        assert range_obj.start_date == date(2026, 1, 1)
        assert range_obj.end_date == date(2026, 12, 31)
        assert range_obj.description == "Year 2026"

    def test_next_month_from_full_month(self):
        """Should navigate to next month when viewing full month."""
        range_obj = TimeNavigator.next_period(date(2025, 1, 1), date(2025, 1, 31))

        assert range_obj.start_date == date(2025, 2, 1)
        assert range_obj.end_date == date(2025, 2, 28)
        assert range_obj.description == "February 2025"

    def test_next_month_across_year_boundary(self):
        """Should navigate from December to January of next year."""
        range_obj = TimeNavigator.next_period(date(2025, 12, 1), date(2025, 12, 31))

        assert range_obj.start_date == date(2026, 1, 1)
        assert range_obj.end_date == date(2026, 1, 31)
        assert range_obj.description == "January 2026"

    def test_next_month_from_january_to_february_leap_year(self):
        """Should handle leap year February correctly."""
        range_obj = TimeNavigator.next_period(date(2024, 1, 1), date(2024, 1, 31))

        assert range_obj.end_date == date(2024, 2, 29)  # Leap year

    def test_next_month_from_january_to_february_non_leap(self):
        """Should handle non-leap year February correctly."""
        range_obj = TimeNavigator.next_period(date(2025, 1, 1), date(2025, 1, 31))

        assert range_obj.end_date == date(2025, 2, 28)  # Non-leap year

    def test_next_month_from_30_day_to_31_day(self):
        """Should handle transition from 30-day to 31-day month."""
        range_obj = TimeNavigator.next_period(
            date(2025, 4, 1),
            date(2025, 4, 30),  # April has 30 days
        )

        assert range_obj.end_date == date(2025, 5, 31)  # May has 31 days

    def test_next_month_from_31_day_to_30_day(self):
        """Should handle transition from 31-day to 30-day month."""
        range_obj = TimeNavigator.next_period(
            date(2025, 5, 1),
            date(2025, 5, 31),  # May has 31 days
        )

        assert range_obj.end_date == date(2025, 6, 30)  # June has 30 days


class TestGetMonthName:
    """Tests for get_month_name method."""

    def test_january(self):
        """Should return 'January' for month 1."""
        assert TimeNavigator.get_month_name(1) == "January"

    def test_december(self):
        """Should return 'December' for month 12."""
        assert TimeNavigator.get_month_name(12) == "December"

    def test_all_months(self):
        """Should return correct names for all months."""
        expected = [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]
        for month, name in enumerate(expected, 1):
            assert TimeNavigator.get_month_name(month) == name

    def test_invalid_month_zero(self):
        """Should raise ValueError for month 0."""
        with pytest.raises(ValueError):
            TimeNavigator.get_month_name(0)

    def test_invalid_month_negative(self):
        """Should raise ValueError for negative month."""
        with pytest.raises(ValueError):
            TimeNavigator.get_month_name(-1)


class TestNavigationEdgeCases:
    """Edge case tests for period navigation."""

    def test_previous_from_year_2000(self):
        """Should navigate from 2000 to 1999."""
        range_obj = TimeNavigator.previous_period(date(2000, 1, 1), date(2000, 12, 31))

        assert range_obj.start_date == date(1999, 1, 1)
        assert range_obj.end_date == date(1999, 12, 31)

    def test_next_to_year_3000(self):
        """Should navigate to year 3000."""
        range_obj = TimeNavigator.next_period(date(2999, 1, 1), date(2999, 12, 31))

        assert range_obj.start_date == date(3000, 1, 1)
        assert range_obj.end_date == date(3000, 12, 31)

    def test_previous_previous_year(self):
        """Should handle double previous navigation."""
        range1 = TimeNavigator.previous_period(date(2025, 1, 1), date(2025, 12, 31))
        range2 = TimeNavigator.previous_period(range1.start_date, range1.end_date)

        assert range2.start_date == date(2023, 1, 1)
        assert range2.end_date == date(2023, 12, 31)

    def test_next_next_month(self):
        """Should handle double next navigation."""
        range1 = TimeNavigator.next_period(date(2025, 1, 1), date(2025, 1, 31))
        range2 = TimeNavigator.next_period(range1.start_date, range1.end_date)

        assert range2.start_date == date(2025, 3, 1)
        assert range2.end_date.month == 3


class TestPeriodRoundTrip:
    """Test that navigation is reversible."""

    def test_year_roundtrip(self):
        """next(previous(year)) should return to same year."""
        start = TimeNavigator.get_year_range(2025)
        prev = TimeNavigator.previous_period(start.start_date, start.end_date)
        back = TimeNavigator.next_period(prev.start_date, prev.end_date)

        assert back.start_date == start.start_date
        assert back.end_date == start.end_date

    def test_month_roundtrip(self):
        """next(previous(month)) should return to same month."""
        start = TimeNavigator.get_month_range(2025, 6)
        prev = TimeNavigator.previous_period(start.start_date, start.end_date)
        back = TimeNavigator.next_period(prev.start_date, prev.end_date)

        assert back.start_date == start.start_date
        assert back.end_date == start.end_date

    def test_previous_next_preserves_type(self):
        """Navigation should preserve period type (year stays year)."""
        # Start with year
        year_range = TimeNavigator.get_year_range(2025)
        prev = TimeNavigator.previous_period(year_range.start_date, year_range.end_date)

        # Previous of a year should also be a full year
        assert TimeNavigator.is_full_year_range(prev.start_date, prev.end_date)

        # Next of a month should also be a full month
        month_range = TimeNavigator.get_month_range(2025, 3)
        next_period = TimeNavigator.next_period(month_range.start_date, month_range.end_date)

        assert TimeNavigator.is_full_month_range(next_period.start_date, next_period.end_date)


class TestDescriptions:
    """Tests for date range descriptions."""

    def test_month_description_format(self):
        """Month descriptions should be 'MonthName YYYY'."""
        range_obj = TimeNavigator.get_month_range(2025, 6)
        assert range_obj.description == "June 2025"

    def test_year_description_format(self):
        """Year descriptions should be 'Year YYYY'."""
        range_obj = TimeNavigator.get_year_range(2025)
        assert range_obj.description == "Year 2025"

    def test_navigation_preserves_meaningful_descriptions(self):
        """Navigated ranges should have clear descriptions."""
        start = TimeNavigator.get_month_range(2025, 1)
        next_month = TimeNavigator.next_period(start.start_date, start.end_date)

        assert "February" in next_month.description
        assert "2025" in next_month.description
