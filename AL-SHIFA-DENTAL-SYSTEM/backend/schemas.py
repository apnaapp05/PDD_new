# backend/schemas.py

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# --- USER & AUTH ---
class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    email: str
    password: str
    full_name: str
    role: str 
    hospital_name: Optional[str] = None
    address: Optional[str] = None
    pincode: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    specialization: Optional[str] = None
    license_number: Optional[str] = None
    scheduling_config: Optional[dict] = None

class UserOut(UserBase):
    id: int
    full_name: str
    role: str
    is_email_verified: bool
    phone_number: Optional[str] = None
    address: Optional[str] = None
    # Add these fields so the frontend can read them
    specialization: Optional[str] = None
    license_number: Optional[str] = None
    
    class Config:
        from_attributes = True

# FIX: Added Doctor fields here
class UserProfileUpdate(BaseModel):
    full_name: str
    email: str
    phone_number: Optional[str] = None
    address: Optional[str] = None
    specialization: Optional[str] = None  # NEW
    license_number: Optional[str] = None  # NEW

# --- AUTH ---
class Login(BaseModel):
    username: str
    password: str

class VerifyOTP(BaseModel):
    email: str
    otp: str

# --- ORGANIZATION ---
class LocationUpdate(BaseModel):
    address: str
    pincode: str
    lat: float
    lng: float

# --- DOCTOR ---
class DoctorJoinRequest(BaseModel):
    hospital_id: int
    specialization: str
    license_number: str

class BlockSlotCreate(BaseModel):
    date: str
    time: Optional[str] = None
    reason: str
    is_whole_day: bool = False

# --- APPOINTMENTS ---
class AppointmentCreate(BaseModel):
    doctor_id: int
    date: str
    time: str
    reason: str

class PatientProfileUpdate(BaseModel):
    full_name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    blood_group: Optional[str] = None

# --- INVENTORY ---
class InventoryItemCreate(BaseModel):
    name: str
    quantity: int
    unit: str
    threshold: int = 10

class InventoryUpdate(BaseModel):
    quantity: int

# --- MEDICAL RECORDS ---
class RecordCreate(BaseModel):
    diagnosis: str
    prescription: str
    notes: str

# --- PATIENT CREATION BY DOCTOR ---
class PatientCreateByDoctor(BaseModel):
    full_name: str
    email: str
    age: int
    gender: str

# --- TREATMENTS ---
class TreatmentCreate(BaseModel):
    name: str
    cost: float
    description: Optional[str] = None

class TreatmentLinkCreate(BaseModel):
    item_id: int
    quantity: int

class InventoryItemRef(BaseModel):
    name: str
    unit: str
    class Config:
        from_attributes = True

class TreatmentLinkOut(BaseModel):
    quantity_required: int
    item: InventoryItemRef
    class Config:
        from_attributes = True

class TreatmentOut(BaseModel):
    id: int
    name: str
    cost: float
    description: Optional[str]
    required_items: List[TreatmentLinkOut] = []
    class Config:
        from_attributes = True

# --- INVOICES ---
class InvoiceOut(BaseModel):
    id: int
    amount: float
    status: str
    created_at: datetime
    patient_name: str
    treatment_type: str

# --- CLINICAL CASES ---
class CaseCreate(BaseModel):
    patient_id: int
    title: str
    stage: str

class CaseUpdate(BaseModel):
    stage: str
    status: Optional[str] = None

class CaseOut(BaseModel):
    id: int
    title: str
    stage: str
    status: str
    updated_at: datetime
    patient_name: str
    class Config:
        from_attributes = True
# --- AGENT SCHEMAS ---
class BookingRequest(BaseModel):
    user_query: str
    patient_id: str
    patient_name: str
