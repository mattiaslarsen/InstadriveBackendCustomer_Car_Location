# Models/__init__.py
from .base import Base
from .customer import Customer
from .location import Location
from .car import Car

# List all models for easy access and database initialization
__all__ = [
    'Base',
    'Customer',
    'Location',
    'Car'
]

# Export models to make them available when importing from models package
Base = Base
Customer = Customer
Location = Location
Car = Car