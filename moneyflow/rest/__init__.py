"""
REST API server for moneyflow.

Exposes the same entry points as the MCP server through a FastAPI HTTP interface.
"""

from .server import create_rest_app, run_rest_server

__all__ = ["create_rest_app", "run_rest_server"]
