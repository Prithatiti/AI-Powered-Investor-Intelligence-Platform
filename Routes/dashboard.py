"""InvestorIQ AI - metrics dashboard API route.

Exposes the latest extracted financial KPIs from PostgreSQL so the UI can
render company scorecards.  For every (company, year) pair only the most
recently created row is returned.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from Database.postgres_connect import CreateEngine

router = APIRouter()

_LATEST_METRICS_QUERY = """
    SELECT *
    FROM (
        SELECT *,
               ROW_NUMBER() OVER (
                   PARTITION BY company, year
                   ORDER BY created_at DESC
               ) AS rn
        FROM financial_metrics
    ) t
    WHERE rn = 1
    ORDER BY company
"""

_engine = None


def _get_engine():
    """Return a lazily-created SQLAlchemy engine for the PostgreSQL database."""
    global _engine
    if _engine is None:
        _engine = CreateEngine(
            database=os.getenv(key="POSTGRES_DATABASE", default="investoriq")
        )
    return _engine


def _to_json_safe(value: Any) -> Any:
    """Convert non-JSON-serialisable values (e.g. datetimes) for the API."""
    if isinstance(value, datetime):
        return value.isoformat()
    return value


@router.get(path="/metrics")
async def get_metrics():
    """Return the latest metrics row per (company, year) pair.

    Returns
    -------
    dict
        A count plus the list of ``financial_metrics`` rows ordered by
        company name.

    Raises
    ------
    HTTPException
        500 when the metrics table cannot be queried.
    """
    try:
        with _get_engine().connect() as conn:
            result = conn.execute(text(text=_LATEST_METRICS_QUERY))
            columns = list(result.keys())
            rows = [
                {col: _to_json_safe(value) for col, value in zip(columns, row)}
                for row in result.fetchall()
            ]
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to query financial metrics: {exc}",
        ) from exc

    return {"count": len(rows), "metrics": rows}