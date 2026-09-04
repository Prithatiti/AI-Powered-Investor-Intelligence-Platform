"""
Save Metrics to PostgreSQL
==========================

Persists extracted financial KPIs into the ``financial_metrics`` table.

Accepts the Pydantic ``FinancialMetrics`` model produced by the KPI
extractor (or any dict / object with the same field names) and inserts
a single row per company-year pair.

Usage:
    # As an import
    from Database.save_metrics import SaveMetrics

    SaveMetrics(engine, metrics, company="Apple", year="2024")

    # Standalone — inserts dummy test data then exits
    python -m Database.save_metrics
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.engine import Engine

from Database.create_table import Base, FinancialMetrics


# ---------------------------------------------------------------------------
# Helper: coerce a value to a JSON-safe string for TEXT columns
# ---------------------------------------------------------------------------
def _to_text(value: Any) -> str | None:
    """Convert *value* to a string suitable for a TEXT column.

    - ``None`` stays ``None``.
    - Lists / dicts are serialised to JSON.
    - Everything else is cast with ``str()``.
    """
    if value is None:
        return None
    if isinstance(value, (list, dict)):
        return json.dumps(obj=value, ensure_ascii=False)
    return str(object=value)


# ---------------------------------------------------------------------------
# SaveMetrics
# ---------------------------------------------------------------------------
def SaveMetrics(
    engine: Engine,
    metrics: Any,
    company: str,
    year: str | int,
) -> None:
    """Insert a single row of financial metrics into PostgreSQL.

    Parameters
    ----------
    engine : sqlalchemy.Engine
        Database engine (from :func:`Database.postgres_connect.CreateEngine`).
    metrics : Any
        Object whose attributes match the KPI fields (Pydantic model,
        dataclass, or plain dict).  Recognised attribute names:
        ``revenue``, ``net_income``, ``operating_income``, ``cash_flow``,
        ``total_assets``, ``total_liabilities``, ``key_risk_factors``,
        ``growth_drivers``, ``executive_summary``.
    company : str
        Company name.
    year : str | int
        Report year.
    """
    row = FinancialMetrics(
        company=company,
        year=str(object=year),
        revenue=_to_text(value=_get(obj=metrics, name="revenue")),
        net_income=_to_text(value=_get(obj=metrics, name="net_income")),
        operating_income=_to_text(value=_get(obj=metrics, name="operating_income")),
        cash_flow=_to_text(value=_get(obj=metrics, name="cash_flow")),
        total_assets=_to_text(value=_get(obj=metrics, name="total_assets")),
        total_liabilities=_to_text(value=_get(obj=metrics, name="total_liabilities")),
        risk_factors=_to_text(
            value=_get(obj=metrics, name="key_risk_factors") or _get(obj=metrics, name="risk_factors")
        ),
        growth_drivers=_to_text(value=_get(obj=metrics, name="growth_drivers")),
        executive_summary=_to_text(value=_get(obj=metrics, name="executive_summary")),
    )

    with engine.begin() as conn:
        conn.execute(
            statement=Base.metadata.tables["financial_metrics"].insert(),
            parameters={
                "company": row.company,
                "year": row.year,
                "revenue": row.revenue,
                "net_income": row.net_income,
                "operating_income": row.operating_income,
                "cash_flow": row.cash_flow,
                "total_assets": row.total_assets,
                "total_liabilities": row.total_liabilities,
                "risk_factors": row.risk_factors,
                "growth_drivers": row.growth_drivers,
                "executive_summary": row.executive_summary,
            },
        )

    print(
        f"[OK] Saved metrics for {company} ({year}) "
        f"into 'financial_metrics' table."
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _get(obj: Any, name: str) -> Any:
    """Read an attribute from *obj* (dict or object)."""
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


# ---------------------------------------------------------------------------
# Standalone entry-point — insert dummy metrics for testing
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import os

    from Database.postgres_connect import CreateDatabase, CreateEngine

    db_name = os.getenv(key="POSTGRES_DATABASE", default="investoriq")

    CreateDatabase()
    engine = CreateEngine(database=db_name)

    # --- Dummy test data (will be deleted later) ---
    dummy_data = [
        {
            "company": "Apple",
            "year": "2024",
            "revenue": "$394.3 billion",
            "net_income": "$93.7 billion",
            "operating_income": "$123.2 billion",
            "cash_flow": "$118.3 billion",
            "total_assets": "$352.8 billion",
            "total_liabilities": "$290.4 billion",
            "key_risk_factors": [
                "Supply chain disruptions",
                "Regulatory scrutiny in the EU",
                "Foreign exchange volatility",
            ],
            "growth_drivers": [
                "Services revenue growth",
                "iPhone 16 cycle",
                "AI-powered features (Apple Intelligence)",
            ],
            "executive_summary": [
                "Apple delivered record revenue driven by strong services growth.",
                "Gross margin expanded to 46.2% on favourable product mix.",
            ],
        },
        {
            "company": "Microsoft",
            "year": "2024",
            "revenue": "$245.1 billion",
            "net_income": "$88.1 billion",
            "operating_income": "$109.4 billion",
            "cash_flow": "$89.0 billion",
            "total_assets": "$484.0 billion",
            "total_liabilities": "$251.0 billion",
            "key_risk_factors": [
                "Antitrust investigations in the US and EU",
                "Slowing PC demand",
                "Azure capacity constraints",
            ],
            "growth_drivers": [
                "Azure cloud revenue acceleration",
                "Copilot AI subscription adoption",
                "LinkedIn and Gaming segments",
            ],
            "executive_summary": [
                "Microsoft posted double-digit revenue growth across all segments.",
                "Cloud revenue surpassed $105 billion run-rate.",
            ],
        },
    ]

    for entry in dummy_data:
        company = entry.pop("company")
        year = entry.pop("year")
        SaveMetrics(engine=engine, metrics=entry, company=str(object=company), year=str(object=year))

    print("\n[DONE] All dummy metrics inserted.")
