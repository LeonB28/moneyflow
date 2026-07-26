import asyncio
import webbrowser
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import polars as pl

from ..backends.boi import BankOfIreland
from ..data.data_manager import DataManager


def _compute_income_vs_spent(df: pl.DataFrame) -> dict:
    visible = df.filter(~pl.col("hideFromReports"))
    income = visible.filter(pl.col("amount") > 0)["amount"].sum()
    spent = visible.filter(pl.col("amount") < 0)["amount"].abs().sum()
    return {"income": income, "spent": spent}


def _compute_spending_by_group(df: pl.DataFrame) -> pl.DataFrame:
    return (
        df.filter(pl.col("amount") < 0, ~pl.col("hideFromReports"))
        .group_by("group")
        .agg(pl.col("amount").abs().sum().alias("total"))
        .sort("total", descending=True)
    )


def _build_html(
    income_vs_spent: dict,
    spending_by_group: pl.DataFrame,
    start_date: date,
    end_date: date,
) -> str:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    fig = make_subplots(
        rows=1,
        cols=2,
        specs=[[{"type": "bar"}, {"type": "pie"}]],
        subplot_titles=("Income vs Spent", "Spending by Category Group"),
    )

    fig.add_trace(
        go.Bar(
            x=["Income", "Spent"],
            y=[income_vs_spent["income"], income_vs_spent["spent"]],
            marker_color=["#2ecc71", "#e74c3c"],
            text=[f"${v:,.2f}" for v in [income_vs_spent["income"], income_vs_spent["spent"]]],
            textposition="outside",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Pie(
            labels=spending_by_group["group"].to_list(),
            values=spending_by_group["total"].to_list(),
            textinfo="label+percent",
            hovertemplate="%{label}<br>$%{value:,.2f}<extra></extra>",
        ),
        row=1,
        col=2,
    )

    fig.update_layout(
        title_text=f"Financial Dashboard — {start_date} to {end_date}",
        height=500,
        width=1200,
        showlegend=False,
        template="plotly_white",
    )
    fig.update_yaxes(title_text="Amount ($)", row=1, col=1)

    return fig.to_html(include_plotlyjs="cdn", full_html=True, config={"responsive": True})


def generate_report(
    days: int = 30,
    output: Optional[str] = None,
    open_browser: bool = False,
) -> str:
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    backend = BankOfIreland()
    dm = DataManager(mm=backend, config_dir=str(Path.home() / ".moneyflow"))

    df, _categories, _category_groups = asyncio.run(
        dm.fetch_all_data(
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
        )
    )

    income_vs_spent = _compute_income_vs_spent(df)
    spending_by_group = _compute_spending_by_group(df)

    html = _build_html(income_vs_spent, spending_by_group, start_date, end_date)

    if output:
        out_path = Path(output)
    else:
        reports_dir = Path.home() / ".moneyflow" / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        out_path = reports_dir / f"dashboard_{start_date.isoformat()}_{end_date.isoformat()}.html"

    out_path.write_text(html)

    if open_browser:
        webbrowser.open(f"file://{out_path.resolve()}")

    return str(out_path)
