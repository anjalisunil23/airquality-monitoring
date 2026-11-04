"""
Configuration settings for the Smart Classroom Environmental Monitoring System.
Includes configurable temperature and humidity thresholds, database settings, and device status timings.
"""
import os
from typing import Dict, Any

# ==============================================================================
# Database Configuration
# ==============================================================================
# Use PostgreSQL if DATABASE_URL is provided, otherwise default to PostgreSQL localhost
# or fallback to local SQLite for frictionless local development.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/classroom_db"
)

# ==============================================================================
# Device Monitoring Settings
# ==============================================================================
# If no reading arrives for DEVICE_TIMEOUT_SECONDS, device is flagged Offline
DEVICE_TIMEOUT_SECONDS = int(os.getenv("DEVICE_TIMEOUT_SECONDS", "15"))
DEFAULT_DEVICE_ID = "esp32-classroom-01"

# ==============================================================================
# Configurable Temperature Thresholds (°C)
# - Below 18°C: Cool
# - 18°C–24°C: Comfortable
# - Above 24°C–30°C: Warm
# - Above 30°C: Hot
# ==============================================================================
TEMP_THRESHOLDS = {
    "cool_max": float(os.getenv("TEMP_COOL_MAX", "18.0")),
    "comfortable_max": float(os.getenv("TEMP_COMFORTABLE_MAX", "25.0")),
    "warm_max": float(os.getenv("TEMP_WARM_MAX", "30.0")),
}

# ==============================================================================
# Configurable Relative Humidity Thresholds (%)
# - Below 30%: Low humidity
# - 30%–60%: Normal range
# - Above 60%–70%: Elevated humidity
# - Above 70%: High humidity
# ==============================================================================
HUMIDITY_THRESHOLDS = {
    "low_max": float(os.getenv("HUMIDITY_LOW_MAX", "30.0")),
    "normal_max": float(os.getenv("HUMIDITY_NORMAL_MAX", "60.0")),
    "elevated_max": float(os.getenv("HUMIDITY_ELEVATED_MAX", "70.0")),
}


def get_temperature_status(temp: float) -> Dict[str, Any]:
    """
    Evaluate temperature against configured project thresholds.
    Returns status label, code, and recommended theme accent.
    """
    if temp < TEMP_THRESHOLDS["cool_max"]:
        return {
            "status": "Cool",
            "code": "cool",
            "description": f"Below {TEMP_THRESHOLDS['cool_max']}°C (Cool)",
            "accent": "#0284c7",  # Sky Blue
            "badge_class": "badge-cool"
        }
    elif temp <= TEMP_THRESHOLDS["comfortable_max"]:
        return {
            "status": "Comfortable",
            "code": "comfortable",
            "description": f"{TEMP_THRESHOLDS['cool_max']}°C–{TEMP_THRESHOLDS['comfortable_max']}°C (Comfortable)",
            "accent": "#16a34a",  # Fresh Green
            "badge_class": "badge-comfortable"
        }
    elif temp <= TEMP_THRESHOLDS["warm_max"]:
        return {
            "status": "Warm",
            "code": "warm",
            "description": f"{TEMP_THRESHOLDS['comfortable_max']}°C–{TEMP_THRESHOLDS['warm_max']}°C (Warm)",
            "accent": "#ea580c",  # Warm Orange
            "badge_class": "badge-warm"
        }
    else:
        return {
            "status": "Hot",
            "code": "hot",
            "description": f"Above {TEMP_THRESHOLDS['warm_max']}°C (Hot)",
            "accent": "#dc2626",  # Alert Red
            "badge_class": "badge-hot"
        }


def get_humidity_status(humidity: float) -> Dict[str, Any]:
    """
    Evaluate humidity against configured project thresholds.
    Returns status label, code, and recommended theme accent.
    """
    if humidity < HUMIDITY_THRESHOLDS["low_max"]:
        return {
            "status": "Low",
            "code": "low",
            "description": f"Below {HUMIDITY_THRESHOLDS['low_max']}% (Low)",
            "accent": "#d97706",  # Amber
            "badge_class": "badge-hum-low"
        }
    elif humidity <= HUMIDITY_THRESHOLDS["normal_max"]:
        return {
            "status": "Normal",
            "code": "normal",
            "description": f"{HUMIDITY_THRESHOLDS['low_max']}%–{HUMIDITY_THRESHOLDS['normal_max']}% (Normal)",
            "accent": "#059669",  # Emerald Green
            "badge_class": "badge-hum-normal"
        }
    elif humidity <= HUMIDITY_THRESHOLDS["elevated_max"]:
        return {
            "status": "Elevated",
            "code": "elevated",
            "description": f"{HUMIDITY_THRESHOLDS['normal_max']}%–{HUMIDITY_THRESHOLDS['elevated_max']}% (Elevated)",
            "accent": "#0284c7",  # Blue
            "badge_class": "badge-hum-elevated"
        }
    else:
        return {
            "status": "High",
            "code": "high",
            "description": f"Above {HUMIDITY_THRESHOLDS['elevated_max']}% (High)",
            "accent": "#e11d48",  # Rose Red
            "badge_class": "badge-hum-high"
        }
