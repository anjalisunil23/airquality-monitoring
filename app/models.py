"""
SQLAlchemy ORM models for Smart Classroom Environmental Monitoring System.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, DateTime
from app.database import Base


def get_current_time():
    """Returns the current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class Reading(Base):
    """
    Sensor reading record received from ESP32 with DHT22.
    """
    __tablename__ = "readings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    temperature = Column(Float, nullable=False, comment="Temperature in Celsius")
    humidity = Column(Float, nullable=False, comment="Relative Humidity in percentage")
    timestamp = Column(DateTime(timezone=True), default=get_current_time, nullable=False, index=True)
    device_id = Column(String(64), default="esp32-classroom-01", nullable=False, index=True)

    def __repr__(self):
        return f"<Reading(id={self.id}, temp={self.temperature}°C, hum={self.humidity}%, time={self.timestamp})>"
