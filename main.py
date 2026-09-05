"""InvestorIQ AI — FastAPI application entry-point.

Creates the FastAPI app, enables CORS (so the frontend can call the API from
a browser), and mounts the Routers.

Run locally:
    uvicorn main:app --reload
"""

import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from Routes.chat import router as chat_router
from Routes.dashboard import router as dashboard_router
from Routes.health import router as health_router
from Routes.ingestion import router as ingestion_router

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

load_dotenv(dotenv_path=f"{PROJECT_ROOT}/.env")

app = FastAPI(
    title="InvestorIQ AI — Investor Intelligence Platform",
    description=(
        "AI-powered investor intelligence platform that ingests annual "
        "reports, extracts financial KPIs, and answers contextual questions."
    ),
    version="0.1.0",
)

# Allow the UI (served from a different origin / port) to call this API.
app.add_middleware(
    middleware_class=CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv(key="CORS_ALLOW_ORIGINS", default="*").split(sep=",")
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routers
app.include_router(health_router)
app.include_router(ingestion_router)
app.include_router(dashboard_router)
app.include_router(chat_router)


if __name__ == "__main__":
    uvicorn.run(
        app="main:app",
        host=os.getenv(key="API_HOST", default="0.0.0.0"),
        port=int(os.getenv(key="API_PORT", default="8000")),
        reload=True,
    )