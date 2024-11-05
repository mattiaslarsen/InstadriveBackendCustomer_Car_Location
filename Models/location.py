# Models/location.py
from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

class Location(Base):
    __tablename__ = 'locations'

    # Primary identifiers
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)

    # Value Objects
    address = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    # Location type flags
    is_pickup_location = Column(Boolean, default=True)
    is_dropoff_location = Column(Boolean, default=True)

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships will be added when Car model is implemented
    cars = relationship("Car", back_populates="location")
    
    def __repr__(self):
        return f"<Location {self.name} ({self.address})>"