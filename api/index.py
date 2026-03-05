import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="WhatsApp Broadcast API")

# CORS — allow Vercel frontend and localhost dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://whatsappbroadcastsjg.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and mount the full broadcasts router (all CRUD + webhook endpoints)
_import_error = None
try:
    from broadcasts.router import router as broadcasts_router
    from broadcasts.database import init_db, close_db
    app.include_router(broadcasts_router, prefix="/api/broadcasts", tags=["Broadcasts"])
    logger.info("Broadcasts router mounted successfully")
except Exception as e:
    _import_error = str(e)
    logger.error(f"Failed to import broadcasts module: {e}")

# Health check — always available, shows import errors for debugging
@app.get("/api/health")
async def health():
    if _import_error:
        return {"status": "degraded", "message": "API running but broadcasts module failed to load", "error": _import_error}
    return {"status": "ok", "message": "API is running on Vercel"}

@app.on_event("startup")
async def startup():
    if _import_error:
        logger.warning(f"Skipping DB init — broadcasts module failed: {_import_error}")
        return
    try:
        logger.info("Starting up... initializing database")
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.warning(f"Database initialization failed: {e}. Continuing without database.")

@app.on_event("shutdown")
async def shutdown():
    if _import_error:
        return
    try:
        await close_db()
    except Exception as e:
        logger.warning(f"Error during shutdown: {e}")

logger.info("All routes registered successfully")


