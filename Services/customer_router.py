# Services/customer_router.py
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query, status
from sqlalchemy import exc
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, constr
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import csv
import io
import json
from Models import Customer
from database import get_db

router = APIRouter()

# Pydantic models with strict validation
class CustomerBase(BaseModel):
    name: constr(min_length=2, max_length=100)
    email: EmailStr
    phone: Optional[constr(max_length=20)] = None
    address: Optional[constr(max_length=200)] = None
    preferences: Dict[str, Any] = {}

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(CustomerBase):
    is_active: Optional[bool] = None
    verified: Optional[bool] = None

class CustomerResponse(CustomerBase):
    id: str
    is_active: bool
    verified: bool
    created_at: datetime
    updated_at: Optional[datetime]
    last_login: Optional[datetime]

    class Config:
        orm_mode = True

class ImportResult(BaseModel):
    successful: int = 0
    failed: List[Dict[str, str]] = []
    total: int = 0

# Helper functions
def parse_preferences(preferences_str: str) -> Dict:
    """Safely parse JSON preferences string."""
    try:
        if isinstance(preferences_str, dict):
            return preferences_str
        return json.loads(preferences_str)
    except (json.JSONDecodeError, TypeError):
        return {}

# API Endpoints
@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    customer: CustomerCreate,
    db: Session = Depends(get_db)
):
    try:
        db_customer = Customer(
            id=str(uuid.uuid4()),
            **customer.dict(),
            created_at=datetime.utcnow()
        )
        db.add(db_customer)
        db.commit()
        db.refresh(db_customer)
        return db_customer
    except exc.IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

@router.get("/list", response_model=List[CustomerResponse])
async def list_customers(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    active_only: bool = Query(default=True),
    db: Session = Depends(get_db)
):
    query = db.query(Customer)
    if active_only:
        query = query.filter(Customer.is_active == True)
    return query.offset(skip).limit(limit).all()

@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: str,
    db: Session = Depends(get_db)
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    return customer

@router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: str,
    customer: CustomerUpdate,
    db: Session = Depends(get_db)
):
    db_customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not db_customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    update_data = customer.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_customer, field, value)

    db_customer.updated_at = datetime.utcnow()

    try:
        db.commit()
        db.refresh(db_customer)
        return db_customer
    except exc.IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists"
        )

@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: str,
    db: Session = Depends(get_db)
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    customer.is_active = False
    customer.updated_at = datetime.utcnow()
    db.commit()
    return None

@router.post("/import", response_model=ImportResult)
async def import_customers(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith('.tsv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only TSV files are supported"
        )

    content = await file.read()
    return await import_customers_from_tsv(content, db)

async def import_customers_from_tsv(content: bytes, db: Session) -> ImportResult:
    result = ImportResult()

    try:
        tsv_file = io.StringIO(content.decode('utf-8'))
        reader = csv.DictReader(tsv_file, delimiter='\t')

        required_fields = {'name', 'email'}
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
                customer_data = {
                    'id': str(uuid.uuid4()),
                    'name': row['name'].strip(),
                    'email': row['email'].strip(),
                    'phone': row.get('phone', '').strip() or None,
                    'address': row.get('address', '').strip() or None,
                    'preferences': parse_preferences(row.get('preferences', '{}')),
                    'is_active': True,
                    'verified': False,
                    'created_at': datetime.utcnow()
                }
                batch.append(Customer(**customer_data))

                if len(batch) >= batch_size:
                    db.bulk_save_objects(batch)
                    result.successful += len(batch)
                    batch = []

            except Exception as e:
                result.failed.append({
                    'row': str(result.total),
                    'error': str(e)
                })

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