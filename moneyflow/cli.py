"""
Command-line interface for moneyflow.

Provides Click-based CLI for launching moneyflow in different modes
(Monarch, Amazon, Demo) and managing data imports.
"""

import click


@click.group(invoke_without_command=True)
@click.option(
    "--year",
    type=int,
    metavar="YYYY",
    help="Only load transactions from this year onwards (e.g., --year 2025)",
)
@click.option(
    "--since",
    type=str,
    metavar="YYYY-MM-DD",
    help="Only load transactions from this date onwards (overrides --year)",
)
@click.option(
    "--mtd", is_flag=True, help="Load month-to-date transactions (from 1st of current month)"
)
@click.option(
    "--cache", type=str, metavar="PATH", help="Enable caching. Optionally specify cache directory"
)
@click.option("--refresh", is_flag=True, help="Force refresh from API, skip cache even if valid")
@click.option(
    "--demo", is_flag=True, help="Run in demo mode with sample data (no authentication required)"
)
@click.pass_context
def cli(ctx, year, since, mtd, cache, refresh, demo):
    """moneyflow - Terminal UI for personal finance management.

    Run with no arguments to launch Monarch Money mode (default).
    Use subcommands for other modes (e.g., 'moneyflow amazon').
    """
    # If a subcommand is provided, don't launch monarch mode
    if ctx.invoked_subcommand is not None:
        return

    # Launch Monarch Money mode (default)
    from moneyflow.app import launch_monarch_mode

    launch_monarch_mode(
        year=year,
        since=since,
        mtd=mtd,
        cache=cache,
        refresh=refresh,
        demo=demo,
    )


@cli.group(invoke_without_command=True)
@click.option(
    "--db-path",
    type=click.Path(),
    default=None,
    help="Path to Amazon SQLite database (default: ~/.moneyflow/amazon.db)",
)
@click.pass_context
def amazon(ctx, db_path):
    """Amazon purchase analysis mode.

    Run 'moneyflow amazon' to launch the UI.
    Use subcommands for import/status operations.
    """
    # Store db_path in context for subcommands
    ctx.ensure_object(dict)
    ctx.obj["db_path"] = db_path

    # If no subcommand, launch the UI
    if ctx.invoked_subcommand is None:
        from moneyflow.app import launch_amazon_mode
        from moneyflow.backends.amazon import AmazonBackend

        backend = AmazonBackend(db_path=db_path)

        # Check if database exists
        if not backend.db_path.exists():
            click.echo("No Amazon data found.")
            click.echo("\nPlease import your Amazon purchase data first:")
            click.echo("  $ moneyflow amazon import ~/Downloads/amazon-purchases.csv")
            click.echo("\nFor help:")
            click.echo("  $ moneyflow amazon --help")
            raise click.Abort()

        # Check if database has data
        stats = backend.get_database_stats()
        if stats["total_transactions"] == 0:
            click.echo("Amazon database is empty.")
            click.echo("\nPlease import your Amazon purchase data:")
            click.echo("  $ moneyflow amazon import ~/Downloads/amazon-purchases.csv")
            raise click.Abort()

        # Launch the UI
        launch_amazon_mode(db_path=db_path)


@amazon.command(name="import")
@click.pass_context
@click.argument("csv_path", type=click.Path(exists=True))
@click.option("--force", is_flag=True, help="Force reimport of duplicates (overwrites existing)")
def amazon_import(ctx, csv_path, force):
    """Import Amazon purchases from CSV file.

    Expected CSV format:
    Order Date, Title, Category, Quantity, Item Total, ...

    Example:
        moneyflow amazon import ~/Downloads/amazon-purchases.csv
    """
    from moneyflow.backends.amazon import AmazonBackend
    from moneyflow.importers.amazon_csv import import_amazon_csv

    click.echo(f"Importing Amazon purchases from {csv_path}...")

    try:
        db_path = ctx.obj.get("db_path")
        backend = AmazonBackend(db_path=db_path)
        stats = import_amazon_csv(csv_path, backend=backend, force=force)

        click.echo(f"Parsed {stats['total_rows']} items from CSV")

        if stats["categories_created"] > 0:
            click.echo(f"Created {stats['categories_created']} new categories")

        if stats["duplicates"] > 0:
            if force:
                click.echo(f"Updated {stats['duplicates']} existing transactions")
            else:
                click.echo(f"Skipped {stats['duplicates']} duplicates")

        click.echo(f"Imported {stats['imported']} new transactions")

        # Show database stats
        db_stats = backend.get_database_stats()
        click.echo("\nDatabase summary:")
        click.echo(f"  Total transactions: {db_stats['total_transactions']}")
        click.echo(f"  Date range: {db_stats['earliest_date']} to {db_stats['latest_date']}")
        click.echo(f"  Total spent: ${abs(db_stats['total_amount']):,.2f}")
        click.echo(f"  Unique items: {db_stats['item_count']}")
        click.echo(f"  Categories: {db_stats['category_count']}")

        click.echo("\nLaunch moneyflow: $ moneyflow amazon")

    except Exception as e:
        click.echo(f"Import failed: {e}", err=True)
        raise click.Abort()


@amazon.command(name="status")
@click.pass_context
def amazon_status(ctx):
    """Show Amazon database status and import history."""
    from moneyflow.backends.amazon import AmazonBackend

    db_path = ctx.obj.get("db_path")
    backend = AmazonBackend(db_path=db_path)

    # Check if database exists
    if not backend.db_path.exists():
        click.echo("No Amazon data found.")
        click.echo("\nTo import data:")
        click.echo("  $ moneyflow amazon import ~/Downloads/amazon-purchases.csv")
        return

    # Show database stats
    db_stats = backend.get_database_stats()

    click.echo("Amazon Purchase Database")
    click.echo(f"\nLocation: {backend.db_path}")
    click.echo("\nStatistics:")
    click.echo(f"  Total transactions: {db_stats['total_transactions']}")
    click.echo(f"  Date range: {db_stats['earliest_date']} to {db_stats['latest_date']}")
    click.echo(f"  Total spent: ${abs(db_stats['total_amount']):,.2f}")
    click.echo(f"  Unique items: {db_stats['item_count']}")
    click.echo(f"  Categories: {db_stats['category_count']}")

    # Show import history
    history = backend.get_import_history()

    if history:
        click.echo("\nImport History:")
        for record in history[:5]:  # Show last 5 imports
            click.echo(
                f"  {record['import_date']}: {record['filename']} "
                f"({record['record_count']} imported, "
                f"{record['duplicate_count']} duplicates)"
            )

        if len(history) > 5:
            click.echo(f"  ... and {len(history) - 5} more")


if __name__ == "__main__":
    cli()
