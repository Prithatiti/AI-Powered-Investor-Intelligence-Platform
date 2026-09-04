"""
Remove Duplicate Metrics
========================

Removes duplicate rows from the ``financial_metrics`` table, keeping
only the **latest** entry (by ``created_at``) for each unique
``(company, year)`` pair.

Two modes are available:

* **Delete mode** (default) — permanently deletes older duplicates.
* **Dry-run mode** (``--dry-run``) — previews what would be deleted
  without modifying the table.

Usage:
    # As an import
    from Database.remove_duplicate_metrics import RemoveDuplicateMetrics

    RemoveDuplicateMetrics(engine)

    # Standalone
    python -m Database.remove_duplicate_metrics
    python -m Database.remove_duplicate_metrics --dry-run
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine

# ---------------------------------------------------------------------------
# SQL statements
# ---------------------------------------------------------------------------
_DUPLICATE_IDS_CTE = """\
WITH ranked AS (
    SELECT
        id,
        ROW_NUMBER() OVER (
            PARTITION BY company, year
            ORDER BY created_at DESC
        ) AS rn
    FROM financial_metrics
)
SELECT id FROM ranked WHERE rn > 1
"""

_SELECT_LATEST = """\
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


# ---------------------------------------------------------------------------
# RemoveDuplicateMetrics
# ---------------------------------------------------------------------------
def RemoveDuplicateMetrics(
    engine: Engine,
    dry_run: bool = False,
) -> int:
    """Delete older duplicate rows, keeping only the latest per company-year.

    Parameters
    ----------
    engine : sqlalchemy.Engine
        Database engine (from :func:`Database.postgres_connect.CreateEngine`).
    dry_run : bool, optional
        When ``True`` only reports what would be deleted without modifying
        the table.  Defaults to ``False``.

    Returns
    -------
    int
        Number of duplicate rows that were (or would be) removed.
    """
    with engine.begin() as conn:
        # Step 1: identify rows to delete.
        result = conn.execute(text(_DUPLICATE_IDS_CTE))
        ids_to_delete = [row[0] for row in result.fetchall()]

        if not ids_to_delete:
            print("[OK] No duplicate entries found. Table is clean.")
            return 0

        # Step 2: either preview or actually delete.
        if dry_run:
            print(
                f"[DRY RUN] {len(ids_to_delete)} duplicate row(s) "
                f"would be removed (IDs: {ids_to_delete})."
            )
        else:
            placeholders = ", ".join(f":id_{i}" for i in range(len(ids_to_delete)))
            params = {f"id_{i}": rid for i, rid in enumerate(ids_to_delete)}
            conn.execute(
                text(f"DELETE FROM financial_metrics WHERE id IN ({placeholders})"),
                params,
            )
            print(
                f"[OK] Removed {len(ids_to_delete)} duplicate row(s) "
                f"(IDs: {ids_to_delete})."
            )

    return len(ids_to_delete)


# ---------------------------------------------------------------------------
# ShowLatestMetrics — display the de-duplicated result set
# ---------------------------------------------------------------------------
def ShowLatestMetrics(engine: Engine) -> None:
    """Print the latest entry per (company, year) to the console.

    Parameters
    ----------
    engine : sqlalchemy.Engine
        Database engine.
    """
    with engine.connect() as conn:
        result = conn.execute(text(_SELECT_LATEST))
        rows = result.fetchall()

    if not rows:
        print("[INFO] No rows in 'financial_metrics' table.")
        return

    columns = [
        "id", "company", "year", "revenue", "net_income",
        "operating_income", "cash_flow", "total_assets",
        "total_liabilities", "risk_factors", "growth_drivers",
        "executive_summary", "created_at",
    ]

    print(f"\n{'=' * 72}")
    print(f"  Latest metrics per company-year  ({len(rows)} row(s))")
    print(f"{'=' * 72}")

    for row in rows:
        data = dict(zip(columns, row))
        print(
            f"\n  [{data['id']}] {data['company']} - {data['year']}"
            f"  (created: {data['created_at']})"
        )
        print(f"    Revenue        : {data['revenue']}")
        print(f"    Net Income     : {data['net_income']}")
        print(f"    Operating Inc. : {data['operating_income']}")

    print(f"\n{'=' * 72}\n")


# ---------------------------------------------------------------------------
# Standalone entry-point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    import os

    from Database.postgres_connect import CreateDatabase, CreateEngine

    parser = argparse.ArgumentParser(
        description="Remove duplicate financial metrics from PostgreSQL",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview duplicates without deleting them",
    )
    args = parser.parse_args()

    db_name = os.getenv(key="POSTGRES_DATABASE", default="investoriq")

    CreateDatabase()
    engine = CreateEngine(database=db_name)

    removed = RemoveDuplicateMetrics(engine=engine, dry_run=args.dry_run)
    ShowLatestMetrics(engine=engine)

    if not args.dry_run and removed:
        print(f"[DONE] {removed} duplicate(s) removed.")
    elif not args.dry_run:
        print("[DONE] No duplicates to remove.")
