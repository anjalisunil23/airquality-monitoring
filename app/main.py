"""
FastAPI application for Smart Classroom Environmental Monitoring System.
Provides REST API endpoints for ESP32 sensor integration and serves
the light-themed real-time monitoring dashboard.
"""
from datetime import datetime, timezone
import os
from typing import Optional, List
from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db, init_db, ACTIVE_DB_URL, IS_SQLITE
from app.models import Reading
from app.schemas import (
    ReadingCreate,
    ReadingResponse,
    ReadingsListResponse,
    HealthResponse,
    DeviceStatusResponse,
    ThresholdsResponse
)
from app.config import (
    TEMP_THRESHOLDS,
    HUMIDITY_THRESHOLDS,
    DEVICE_TIMEOUT_SECONDS,
    DEFAULT_DEVICE_ID,
    get_temperature_status,
    get_humidity_status
)

app = FastAPI(
    title="Smart Classroom Environmental Monitoring System",
    description="Real-Time Environmental Monitoring with ESP32, DHT22, FastAPI, and PostgreSQL",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for local cross-origin testing / ESP32
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure directories exist
os.makedirs("static/css", exist_ok=True)
os.makedirs("static/js", exist_ok=True)
os.makedirs("templates", exist_ok=True)

# Mount static assets
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
def on_startup():
    """Initialize database tables on application startup"""
    init_db()


def enrich_reading(reading: Reading) -> ReadingResponse:
    """Enriches a database Reading record with dynamic temperature & humidity classification"""
    temp_info = get_temperature_status(reading.temperature)
    hum_info = get_humidity_status(reading.humidity)

    ts = reading.timestamp
    if ts and ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)

    return ReadingResponse(
        id=reading.id,
        temperature=round(reading.temperature, 2),
        humidity=round(reading.humidity, 2),
        timestamp=ts,
        device_id=reading.device_id,
        temp_status=temp_info["status"],
        temp_code=temp_info["code"],
        temp_accent=temp_info["accent"],
        humidity_status=hum_info["status"],
        humidity_code=hum_info["code"],
        humidity_accent=hum_info["accent"]
    )


def compute_device_status(latest_reading: Optional[Reading]) -> DeviceStatusResponse:
    """Calculates online/offline status based strictly on the timestamp of the latest real sensor reading."""
    if not latest_reading:
        return DeviceStatusResponse(
            device_id=DEFAULT_DEVICE_ID,
            online=False,
            status="Offline (No readings received yet)",
            last_seen=None,
            seconds_since_last_reading=None,
            timeout_threshold_seconds=DEVICE_TIMEOUT_SECONDS
        )

    now = datetime.now(timezone.utc)
    ts = latest_reading.timestamp
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)

    diff_seconds = (now - ts).total_seconds()
    is_online = diff_seconds <= DEVICE_TIMEOUT_SECONDS

    return DeviceStatusResponse(
        device_id=latest_reading.device_id,
        online=is_online,
        status="Online" if is_online else f"Offline (Last seen {int(diff_seconds)}s ago)",
        last_seen=latest_reading.timestamp,
        seconds_since_last_reading=round(diff_seconds, 1),
        timeout_threshold_seconds=DEVICE_TIMEOUT_SECONDS
    )


# ==============================================================================
# API Endpoints
# ==============================================================================

@app.get("/health", response_model=HealthResponse, summary="System Health Check")
def get_health(db: Session = Depends(get_db)):
    """
    Health check endpoint returning system status, database connectivity,
    total readings count, and ESP32 connectivity state.
    """
    try:
        total = db.query(Reading).count()
        latest = db.query(Reading).order_by(desc(Reading.id)).first()
        dev_status = compute_device_status(latest)
        enriched_latest = enrich_reading(latest) if latest else None

        db_type = "SQLite (Local fallback)" if IS_SQLITE else "PostgreSQL"

        return HealthResponse(
            status="healthy",
            database="connected",
            database_url_type=db_type,
            total_readings=total,
            device_online=dev_status.online,
            latest_reading=enriched_latest,
            server_time=datetime.now(timezone.utc)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database or service error: {str(e)}"
        )


@app.get("/api/readings/latest", response_model=Optional[ReadingResponse], summary="Latest Sensor Reading")
def get_latest_reading(db: Session = Depends(get_db)):
    """
    Returns the most recent actual sensor reading from the DHT22 through the ESP32.
    Returns 404 if no readings have arrived yet.
    """
    latest = db.query(Reading).order_by(desc(Reading.id)).first()
    if not latest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Waiting for sensor data. No readings received yet."
        )
    return enrich_reading(latest)


@app.get("/api/readings", response_model=ReadingsListResponse, summary="Recent Sensor Readings List")
def get_recent_readings(
    limit: int = Query(30, ge=1, le=200, description="Number of recent readings to fetch"),
    db: Session = Depends(get_db)
):
    """
    Retrieves the latest sensor readings ordered from newest to oldest.
    Includes total count of readings stored in the database.
    """
    total = db.query(Reading).count()
    records = db.query(Reading).order_by(desc(Reading.id)).limit(limit).all()
    enriched = [enrich_reading(r) for r in records]

    return ReadingsListResponse(
        total=total,
        count=len(enriched),
        readings=enriched
    )


@app.post("/api/readings", response_model=ReadingResponse, status_code=status.HTTP_201_CREATED, summary="Submit Reading from ESP32")
def create_reading(payload: ReadingCreate, db: Session = Depends(get_db)):
    """
    Ingests an environmental reading from ESP32 + DHT22:
    - Validates temperature and humidity ranges
    - Stores in PostgreSQL / SQLite
    - Returns enriched response with dynamic classifications
    """
    new_reading = Reading(
        temperature=payload.temperature,
        humidity=payload.humidity,
        device_id=payload.device_id or DEFAULT_DEVICE_ID,
        timestamp=datetime.now(timezone.utc)
    )
    try:
        db.add(new_reading)
        db.commit()
        db.refresh(new_reading)
    except Exception as db_err:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist sensor reading to database: {str(db_err)}"
        )

    return enrich_reading(new_reading)


@app.get("/api/device/status", response_model=DeviceStatusResponse, summary="ESP32 Connectivity Status")
def get_device_status(db: Session = Depends(get_db)):
    """
    Calculates ESP32 connectivity using timestamp difference from latest reading.
    Device is considered Offline if no reading arrived within 15 seconds.
    """
    latest = db.query(Reading).order_by(desc(Reading.id)).first()
    return compute_device_status(latest)


@app.get("/api/thresholds", response_model=ThresholdsResponse, summary="Get Configured Thresholds")
def get_thresholds():
    """Returns current active temperature and humidity thresholds."""
    return ThresholdsResponse(
        temperature=TEMP_THRESHOLDS,
        humidity=HUMIDITY_THRESHOLDS,
        device_timeout_seconds=DEVICE_TIMEOUT_SECONDS
    )


# ==============================================================================
# Web UI Dashboard Routes
# ==============================================================================

@app.get("/", response_class=HTMLResponse, summary="Classroom Monitor Dashboard")
def serve_dashboard():
    """Serves the light-themed environmental monitoring dashboard."""
    index_path = os.path.join("templates", "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(
        content="<h1>Smart Classroom Monitor</h1><p>Dashboard template is initializing...</p>"
    )
