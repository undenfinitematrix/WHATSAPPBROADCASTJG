"""
AeroChat Broadcasts — Application Entry Point
================================================
Run with: uvicorn main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from broadcasts.router import router as broadcasts_router
from broadcasts.database import init_db, close_db

app = FastAPI(title="AeroChat Broadcasts", version="1.0.0")

# Allow React frontend (localhost:3000) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the broadcasts router
app.include_router(broadcasts_router, prefix="/api/broadcasts", tags=["Broadcasts"])


@app.on_event("startup")
async def startup():
    try:
        await init_db()
    except Exception as e:
        # On Vercel, database may not be available (local MySQL)
        # Initialize lazily on first request instead
        import logging
        logging.warning(f"Database initialization on startup failed: {e}. Database will be initialized on first request.")


@app.on_event("shutdown")
async def shutdown():
    await close_db()
