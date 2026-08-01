"""
CLI entry point for the moneyflow REST server.

Run the server with:
    python -m moneyflow.rest [--account ACCOUNT_ID] [--host HOST] [--port PORT]

Or use the CLI command:
    moneyflow-rest [--account ACCOUNT_ID] [--host HOST] [--port PORT]
"""

import argparse
import logging
import sys


def main():
    parser = argparse.ArgumentParser(
        description="Run the moneyflow REST API server (FastAPI)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run on localhost:8000 (default)
    python -m moneyflow.rest

    # Run with specific account
    python -m moneyflow.rest --account my-monarch-account

    # Run on a specific host/port
    python -m moneyflow.rest --host 0.0.0.0 --port 9000

    # Run in read-only mode (no modifications allowed)
    python -m moneyflow.rest --read-only

Security Note:
    This server exposes your financial data over HTTP.
    Only run on trusted networks (localhost or Tailscale).

    There is NO built-in authentication - anyone who can reach the server
    can access your financial data.

    For remote access, ensure you're using a secure network like Tailscale.

Environment Variables:
    MONEYFLOW_PASSWORD  Password for encrypted credentials (if account uses
                        password protection). Required for encrypted accounts
                        since REST server cannot prompt interactively.
""",
    )

    parser.add_argument(
        "--account",
        "-a",
        help="Account ID to use (defaults to last active account)",
    )
    parser.add_argument(
        "--config-dir",
        help="Custom config directory (defaults to ~/.moneyflow)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)",
    )
    parser.add_argument(
        "--read-only",
        "-r",
        action="store_true",
        help="Run in read-only mode (disable all write operations)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Security warning for non-localhost binding
    if args.host not in ("127.0.0.1", "localhost"):
        print(
            "=" * 70,
            "SECURITY WARNING: Non-local bind",
            "=" * 70,
            "",
            "You are running the REST server on a non-local interface.",
            "This server has NO built-in authentication.",
            "",
            "Anyone who can reach this server can:",
            "  - Read all your financial transactions",
            "  - View spending summaries and account details",
            "  - Modify transaction categories (unless --read-only is set)",
            "",
            "Only use non-local bindings on secure networks like Tailscale.",
            "For local use, keep the default 127.0.0.1 binding.",
            "",
            "=" * 70,
            sep="\n",
            file=sys.stderr,
        )

    from .server import run_rest_server

    try:
        run_rest_server(
            account_id=args.account,
            config_dir=args.config_dir,
            host=args.host,
            port=args.port,
            read_only=args.read_only,
        )
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        logging.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
