"""
Monarch Money Power User TUI

A terminal-based interface for fast transaction management.
"""

__version__ = "0.1.0"

from .monarchmoney import MonarchMoney
from .data_manager import DataManager
from .state import AppState, ViewMode, SortMode, TimeFrame, TransactionEdit
from .duplicate_detector import DuplicateDetector

__all__ = [
    "MonarchMoney",
    "DataManager",
    "AppState",
    "ViewMode",
    "SortMode",
    "TimeFrame",
    "TransactionEdit",
    "DuplicateDetector",
]
