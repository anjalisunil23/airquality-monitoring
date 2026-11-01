"""
Pydantic schemas for request validation and response serialization.
"""
import math
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator


class ReadingCreate(BaseModel):
    """Payload sent by ESP32 or test client to POST /api/readings"""
    temperature: float = Field(..., ge=-40.0, le=80.0, description="Temperature in °C")
    humidity: float = Field(..., ge=0.0, le=100.0, description="Relative Humidity in %")
    device_id: Optional[str] = Field("esp32-classroom-01", max_length=64, description="Device Identifier")

    @field_validator("temperature", "humidity")
    @classmethod
    def validate_finite_number(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError("Value must be a valid, finite numeric reading (cannot be NaN or Inf)")
        return v


class ReadingResponse(BaseModel):
    """Serialized sensor reading response with dynamic status classification"""
    id: int
    temperature: float
    humidity: float
    timestamp: datetime
    device_id: str
    temp_status: str
    humidity_status: str
    temp_code: str
    humidity_code: str
    temp_accent: str
    humidity_accent: str

    model_config = ConfigDict(from_attributes=True)


class ReadingsListResponse(BaseModel):
    """Response format for list of historical readings"""
    total: int
    count: int
    readings: List[ReadingResponse]


class DeviceStatusResponse(BaseModel):
    """Device connectivity status evaluated from real sensor activity"""
    device_id: str
    online: bool
    status: str
    last_seen: Optional[datetime] = None
    seconds_since_last_reading: Optional[float] = None
    timeout_threshold_seconds: int


class ThresholdsResponse(BaseModel):
    """Active temperature and humidity threshold definitions"""
    temperature: Dict[str, float]
    humidity: Dict[str, float]
    device_timeout_seconds: int


class HealthResponse(BaseModel):
    """System health check response for /health"""
    status: str
    database: str
    database_url_type: str
    total_readings: int
    device_online: bool
    latest_reading: Optional[ReadingResponse] = None
    server_time: datetime
