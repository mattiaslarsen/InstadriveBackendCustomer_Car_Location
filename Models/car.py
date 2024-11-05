# Models/car.py
from sqlalchemy import Column, String, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

class Car(Base):
    __tablename__ = 'cars'

    # Primary identifiers
    id = Column(String, primary_key=True, index=True)
    license_plate = Column(String, unique=True, nullable=False, index=True)
    vin = Column(String, unique=True, nullable=False)

    # Car details
    make = Column(String, nullable=False)
    model = Column(String, nullable=False)
    year = Column(String, nullable=False)

    # Features and maintenance
    features = Column(JSON, default=dict)
    maintenance_history = Column(JSON, default=list)

    # Status
    is_active = Column(Boolean, default=True)
    is_available = Column(Boolean, default=True)

    # Location relationship
    location_id = Column(String, ForeignKey('locations.id'), nullable=True)
    location = relationship("Location", back_populates="cars")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Car {self.make} {self.model} ({self.license_plate})>"