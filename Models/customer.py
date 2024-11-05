# Models/customer.py
from sqlalchemy import Column, String, DateTime, Boolean, JSON
from datetime import datetime
from .base import Base  # Korrekt - relativ import

class Customer(Base):
    __tablename__ = 'customers'

    # Primary identifiers
    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)

    # Personal information
    name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)

    # Account status
    is_active = Column(Boolean, default=True)
    verified = Column(Boolean, default=False)

    # Preferences
    preferences = Column(JSON, default=dict)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<Customer {self.name} ({self.email})>"