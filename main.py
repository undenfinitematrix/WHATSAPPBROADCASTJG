"""
AeroChat Broadcasts — Application Entry Point
================================================
Run with: uvicorn main:app --reload
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AeroChat Broadcasts", version="1.0.0")

# Allow React frontend (localhost:3000) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://whatsappbroadcastsjg.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint (no database required)
@app.get("/api/health")
async def health():
    return JSONResponse({"status": "ok", "message": "API is running"})

# Import router and database functions
try:
    from broadcasts.router import router as broadcasts_router
    from broadcasts.database import init_db, close_db
    logger.info("Successfully imported router and database modules")
except Exception as e:
    logger.error(f"Failed to import modules: {e}")
    raise

# Mount the broadcasts router
app.include_router(broadcasts_router, prefix="/api/broadcasts", tags=["Broadcasts"])


@app.on_event("startup")
async def startup():
    try:
        logger.info("Starting up... attempting database initialization")
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.warning(f"Database initialization failed: {e}. Continuing without database.")


@app.on_event("shutdown")
async def shutdown():
    try:
        logger.info("Shutting down...")
        await close_db()
    except Exception as e:
        logger.warning(f"Error during shutdown: {e}")
