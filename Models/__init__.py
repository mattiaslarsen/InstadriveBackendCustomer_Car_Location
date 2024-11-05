# Models/__init__.py
from .base import Base
from .customer import Customer
from .location import Location  # New import

# List all models for easy access and database initialization
__all__ = [
    'Base',
    'Customer',
    'Location'
]

# Export models to make them available when importing from models package
Base = Base
Customer = Customer
Location = Location