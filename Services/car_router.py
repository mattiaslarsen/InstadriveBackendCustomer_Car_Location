# Services/car_router.py
from fastapi import APIRouter, HTTPException, Depends, Query, status, UploadFile, File
from sqlalchemy import exc
from sqlalchemy.orm import Session
from pydantic import BaseModel, constr
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
from Models import Car
from database import get_db
import csv
import io
import json

router = APIRouter(
    prefix="/cars",
    tags=["cars"],
    responses={404: {"description": "Car not found"}}
)

class CarBase(BaseModel):
    license_plate: constr(min_length=1, max_length=20)
    vin: constr(min_length=17, max_length=17)
    make: constr(min_length=1, max_length=50)
    model: constr(min_length=1, max_length=50)
    year: constr(min_length=4, max_length=4)
    features: Dict[str, Any] = {}
    maintenance_history: List[Dict[str, Any]] = []
    location_id: Optional[str] = None

class CarCreate(CarBase):
    pass

class CarUpdate(CarBase):
    is_active: Optional[bool] = None
    is_available: Optional[bool] = None

class CarResponse(CarBase):
    id: str
    is_active: bool
    is_available: bool
    created_at: datetime
    updated_at: Optional[datetime]
    location_id: Optional[str]

    class Config:
        orm_mode = True

@router.post("", response_model=CarResponse, status_code=status.HTTP_201_CREATED)
async def create_car(
    car: CarCreate,
    db: Session = Depends(get_db)
):
    db_car = Car(
        id=str(uuid.uuid4()),
        **car.dict(),
        created_at=datetime.utcnow()
    )
    db.add(db_car)
    try:
        db.commit()
        db.refresh(db_car)
        return db_car
    except exc.IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Car with this license plate or VIN already exists"
        )

@router.get("/list", response_model=List[CarResponse])
async def list_cars(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    active_only: bool = Query(default=True),
    available_only: bool = Query(default=False),
    location_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Car)
    if active_only:
        query = query.filter(Car.is_active == True)
    if available_only:
        query = query.filter(Car.is_available == True)
    if location_id:
        query = query.filter(Car.location_id == location_id)
    return query.offset(skip).limit(limit).all()

@router.get("/{car_id}", response_model=CarResponse)
async def get_car(
    car_id: str,
    db: Session = Depends(get_db)
):
    car = db.query(Car).filter(Car.id == car_id).first()
    if not car:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Car not found"
        )
    return car

@router.put("/{car_id}", response_model=CarResponse)
async def update_car(
    car_id: str,
    car: CarUpdate,
    db: Session = Depends(get_db)
):
    db_car = db.query(Car).filter(Car.id == car_id).first()
    if not db_car:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Car not found"
        )

    update_data = car.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_car, field, value)

    db_car.updated_at = datetime.utcnow()

    try:
        db.commit()
        db.refresh(db_car)
        return db_car
    except exc.IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Car update failed due to constraint violation"
        )

@router.delete("/{car_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_car(
    car_id: str,
    db: Session = Depends(get_db)
):
    car = db.query(Car).filter(Car.id == car_id).first()
    if not car:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Car not found"
        )
    car.is_active = False
    car.updated_at = datetime.utcnow()
    db.commit()
    return None