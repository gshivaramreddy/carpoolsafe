"""
CarpoolSafe - Production-Ready Carpooling Platform
FastAPI Backend
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
import os

from models.database import create_tables
from routes import auth, rides, bookings, safety, group_rides, payments
from websocket.tracking import router as tracking_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting CarpoolSafe backend...")
    await create_tables()
    os.makedirs("uploads/profiles", exist_ok=True)
    logger.info("Backend ready.")
    yield
    logger.info("Shutting down backend...")


app = FastAPI(
    title="CarpoolSafe API",
    description="Production-ready carpooling platform with safety features",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if os.path.exists("uploads"):
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Core routes
app.include_router(auth.router)
app.include_router(rides.router)
app.include_router(bookings.router)
app.include_router(safety.router)

# New features
app.include_router(group_rides.router)
app.include_router(payments.router)
app.include_router(tracking_router)
# WebSocket
app.include_router(tracking.router)


@app.get("/")
async def root():
    return {
        "service": "CarpoolSafe API",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
        "features": ["auth", "rides", "bookings", "safety", "group-rides", "payments", "live-tracking"],
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
