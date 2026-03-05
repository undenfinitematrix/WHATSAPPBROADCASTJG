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

# Health check (no database required)
@app.get("/api/health")
async def health():
    return {"status": "ok", "message": "API is running on Vercel"}

# Import and mount the full broadcasts router (all CRUD + webhook endpoints)
try:
    from broadcasts.router import router as broadcasts_router
    from broadcasts.database import init_db, close_db
    app.include_router(broadcasts_router, prefix="/api/broadcasts", tags=["Broadcasts"])
    logger.info("Broadcasts router mounted successfully")
except Exception as e:
    logger.error(f"Failed to import broadcasts module: {e}")
    raise

@app.on_event("startup")
async def startup():
    try:
        logger.info("Starting up... initializing database")
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.warning(f"Database initialization failed: {e}. Continuing without database.")

@app.on_event("shutdown")
async def shutdown():
    try:
        await close_db()
    except Exception as e:
        logger.warning(f"Error during shutdown: {e}")

logger.info("All routes registered successfully")


