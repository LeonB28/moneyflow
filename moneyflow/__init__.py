"""
Monarch Money Power User TUI

A terminal-based interface for fast transaction management.
"""

__version__ = "0.1.0"

from .backends import DemoBackend, FinanceBackend, MonarchBackend, get_backend
from .data_manager import DataManager
from .duplicate_detector import DuplicateDetector
from .monarchmoney import MonarchMoney
from .state import AppState, SortMode, TimeFrame, TransactionEdit, ViewMode

__all__ = [
    "MonarchMoney",
    "FinanceBackend",
    "MonarchBackend",
    "DemoBackend",
    "get_backend",
    "DataManager",
    "AppState",
    "ViewMode",
    "SortMode",
    "TimeFrame",
    "TransactionEdit",
    "DuplicateDetector",
]
