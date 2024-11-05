# Services/location_router.py
from fastapi import APIRouter, HTTPException, Depends, Query, status,UploadFile, File
from sqlalchemy import exc
from sqlalchemy.orm import Session
from pydantic import BaseModel, constr, confloat
from typing import List, Optional, Dict
from datetime import datetime
import uuid
from Models import Location
from database import get_db
import csv
import io

router = APIRouter(
    prefix="/locations",
    tags=["locations"],
    responses={404: {"description": "Location not found"}}
)

class ImportResult(BaseModel):
    successful: int = 0
    failed: List[Dict[str, str]] = []
    total: int = 0

class LocationBase(BaseModel):
    """
    Base location schema with common attributes.

    Attributes:
        name: Location name (e.g., "Downtown Garage")
        address: Full street address
        latitude: Geographic latitude (-90 to 90)
        longitude: Geographic longitude (-180 to 180)
        is_pickup_location: Whether vehicles can be picked up here
        is_dropoff_location: Whether vehicles can be dropped off here
    """
    name: constr(min_length=2, max_length=100)
    address: constr(min_length=5, max_length=200)
    latitude: confloat(ge=-90, le=90)
    longitude: confloat(ge=-180, le=180)
    is_pickup_location: bool = True
    is_dropoff_location: bool = True

class LocationCreate(LocationBase):
    """Schema for creating a new location."""
    pass

class LocationUpdate(LocationBase):
    """
    Schema for updating an existing location.

    Extends LocationBase with optional active status.
    """
    is_active: Optional[bool] = None

class LocationResponse(LocationBase):
    """
    Schema for location responses.

    Extends LocationBase with system-managed fields.
    """
    id: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True

@router.post("", 
    response_model=LocationResponse, 
    status_code=status.HTTP_201_CREATED,
    summary="Create a new location",
    description="""
    Create a new location in the system.

    The location can be designated as a pickup location, dropoff location, or both.
    Requires coordinates and address information.
    """
)
async def create_location(
    location: LocationCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new location with the following steps:
    1. Generate a unique ID
    2. Create database entry
    3. Return the created location
    """
    db_location = Location(
        id=str(uuid.uuid4()),
        **location.dict(),
        created_at=datetime.utcnow()
    )
    db.add(db_location)
    try:
        db.commit()
        db.refresh(db_location)
        return db_location
    except exc.IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Location already exists"
        )

@router.get("/list", 
    response_model=List[LocationResponse],
    summary="List all locations",
    description="""
    Retrieve a list of locations with optional filtering:
    - Filter active/inactive locations
    - Filter pickup/dropoff locations
    - Pagination support
    """
)
async def list_locations(
    skip: int = Query(
        default=0, 
        ge=0, 
        description="Number of locations to skip"
    ),
    limit: int = Query(
        default=100, 
        ge=1, 
        le=1000, 
        description="Maximum number of locations to return"
    ),
    active_only: bool = Query(
        default=True, 
        description="Only return active locations"
    ),
    is_pickup: Optional[bool] = Query(
        default=None, 
        description="Filter by pickup location capability"
    ),
    is_dropoff: Optional[bool] = Query(
        default=None, 
        description="Filter by dropoff location capability"
    ),
    db: Session = Depends(get_db)
):
    """
    List locations with optional filters:
    - Pagination using skip/limit
    - Active status filter
    - Pickup/dropoff capability filters
    """
    query = db.query(Location)

    if active_only:
        query = query.filter(Location.is_active == True)
    if is_pickup is not None:
        query = query.filter(Location.is_pickup_location == is_pickup)
    if is_dropoff is not None:
        query = query.filter(Location.is_dropoff_location == is_dropoff)

    return query.offset(skip).limit(limit).all()

@router.get("/{location_id}", 
    response_model=LocationResponse,
    summary="Get a specific location",
    description="Retrieve detailed information about a specific location by its ID.",
    responses={
        200: {
            "description": "Successful retrieval of location details"
        },
        404: {
            "description": "Location not found"
        }
    }
)
async def get_location(
    location_id: str,
    db: Session = Depends(get_db)
):
    """Retrieve a single location by its ID."""
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found"
        )
    return location

@router.put("/{location_id}", 
    response_model=LocationResponse,
    summary="Update a location",
    description="""
    Update an existing location's details.
    All fields are optional - only provided fields will be updated.
    """,
    responses={
        200: {
            "description": "Successful update of location details"
        },
        404: {
            "description": "Location not found"
        },
        409: {
            "description": "Update failed due to conflict"
        }
    }
)
async def update_location(
    location_id: str,
    location: LocationUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an existing location with new data.
    Only provided fields will be updated.
    """
    db_location = db.query(Location).filter(Location.id == location_id).first()
    if not db_location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found"
        )

    update_data = location.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_location, field, value)

    db_location.updated_at = datetime.utcnow()

    try:
        db.commit()
        db.refresh(db_location)
        return db_location
    except exc.IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Location update failed"
        )

@router.delete("/{location_id}", 
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a location",
    description="""
    Soft-delete a location by marking it as inactive.
    The location record remains in the database but will not be returned in normal queries.
    """,
    responses={
        204: {
            "description": "Location successfully deleted"
        },
        404: {
            "description": "Location not found"
        }
    }
)
async def delete_location(
    location_id: str,
    db: Session = Depends(get_db)
):
    """
    Soft-delete a location by marking it as inactive.
    Does not remove the record from the database.
    """
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found"
        )
    location.is_active = False
    location.updated_at = datetime.utcnow()
    db.commit()
    return None

@router.post("/import", 
    response_model=ImportResult,
    summary="Import locations from TSV file",
    description="""
    Bulk import locations from a TSV (Tab Separated Values) file.

    Required columns:
    - name: Location name
    - address: Full address
    - latitude: Geographic latitude (-90 to 90)
    - longitude: Geographic longitude (-180 to 180)

    Optional columns:
    - is_pickup_location: true/false (default: true)
    - is_dropoff_location: true/false (default: true)
    """
)
async def import_locations(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith('.tsv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only TSV files are supported"
        )

    content = await file.read()
    return await import_locations_from_tsv(content, db)

async def import_locations_from_tsv(content: bytes, db: Session) -> ImportResult:
    result = ImportResult()

    try:
        tsv_file = io.StringIO(content.decode('utf-8'))
        reader = csv.DictReader(tsv_file, delimiter='\t')

        required_fields = {'name', 'address', 'latitude', 'longitude'}
        if not required_fields.issubset(reader.fieldnames):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required fields: {required_fields - set(reader.fieldnames)}"
            )

        batch_size = 100
        batch = []

        for row in reader:
            result.total += 1
            try:
                # Konvertera string-värden till float för koordinater
                try:
                    latitude = float(row['latitude'])
                    longitude = float(row['longitude'])
                    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                        raise ValueError("Invalid coordinates")
                except ValueError as e:
                    raise ValueError(f"Invalid coordinates: lat={row['latitude']}, long={row['longitude']}")

                # Konvertera string-värden till boolean för location-typer
                is_pickup = row.get('is_pickup_location', 'true').lower() == 'true'
                is_dropoff = row.get('is_dropoff_location', 'true').lower() == 'true'

                location_data = {
                    'id': str(uuid.uuid4()),
                    'name': row['name'].strip(),
                    'address': row['address'].strip(),
                    'latitude': latitude,
                    'longitude': longitude,
                    'is_pickup_location': is_pickup,
                    'is_dropoff_location': is_dropoff,
                    'is_active': True,
                    'created_at': datetime.utcnow()
                }
                batch.append(Location(**location_data))

                if len(batch) >= batch_size:
                    db.bulk_save_objects(batch)
                    result.successful += len(batch)
                    batch = []

            except Exception as e:
                result.failed.append({
                    'row': str(result.total),
                    'error': str(e)
                })

        # Spara eventuellt återstående poster i batchen
        if batch:
            db.bulk_save_objects(batch)
            result.successful += len(batch)

        db.commit()

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

    return result