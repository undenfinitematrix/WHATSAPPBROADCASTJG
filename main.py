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
    await init_db()


@app.on_event("shutdown")
async def shutdown():
    await close_db()
