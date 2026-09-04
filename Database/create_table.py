"""
Financial Metrics Table Creator

Creates the ``financial_metrics`` table in PostgreSQL using SQLAlchemy.
The table stores extracted KPIs from annual reports.

Usage:
    # Standalone — creates the database (if needed) then the table
    python -m Database.create_table

    # As an import
    from Database.create_table import CreateFinancialMetricsTable

    CreateFinancialMetricsTable(engine)
"""

from __future__ import annotations

from sqlalchemy import TIMESTAMP, Column, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase


# ---------------------------------------------------------------------------
# ORM model
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


class FinancialMetrics(Base):
    """Row representing extracted financial KPIs for a company-year."""

    __tablename__ = "financial_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company = Column(String(length=100), nullable=False)
    year = Column(String(length=10), nullable=False)
    revenue = Column(Text)
    net_income = Column(Text)
    operating_income = Column(Text)
    cash_flow = Column(Text)
    total_assets = Column(Text)
    total_liabilities = Column(Text)
    risk_factors = Column(Text)
    growth_drivers = Column(Text)
    executive_summary = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())

    def __repr__(self) -> str:
        return (
            f"FinancialMetrics(company={self.company!r}, year={self.year!r})"
        )


# ---------------------------------------------------------------------------
# Table creator
# ---------------------------------------------------------------------------
def CreateFinancialMetricsTable(engine) -> None:
    """Create the ``financial_metrics`` table if it does not exist.

    Parameters
    ----------
    engine : sqlalchemy.Engine
        A SQLAlchemy engine returned by
        :func:`Database.postgres_connect.CreateEngine`.
    """
    Base.metadata.create_all(bind=engine)
    print("[OK] Table 'financial_metrics' is ready.")


# ---------------------------------------------------------------------------
# Standalone entry-point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import os

    from Database.postgres_connect import CreateDatabase, CreateEngine

    db_name = os.getenv(key="POSTGRES_DATABASE", default="investoriq")

    CreateDatabase()
#     engine = CreateEngine(database=db_name)
#     CreateFinancialMetricsTable(engine)
