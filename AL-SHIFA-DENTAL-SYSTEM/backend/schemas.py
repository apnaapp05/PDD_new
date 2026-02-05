from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime
import re

class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str
    role: str
    age: Optional[int] = None
    gender: Optional[str] = None
    hospital_name: Optional[str] = None
    specialization: Optional[str] = None
    phone_number: Optional[str] = None
    address: Optional[str] = None
    dob: Optional[str] = None # Expect YYYY-MM-DD
    
    @validator("phone_number")
    def validate_phone(cls, v):
        if v and not re.match(r"^\d{10}$", v):
            raise ValueError("Phone number must be exactly 10 digits")
        return v

    @validator("full_name")
    def validate_name(cls, v):
        if v and not re.match(r"^[a-zA-Z\s]+$", v):
            raise ValueError("Name must contain alphabets only")
        return v

class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    phone_number: Optional[str] = None
    address: Optional[str] = None
    dob: Optional[datetime] = None 
    specialization: Optional[str] = None

class VerifyOTP(BaseModel):
    email: str
    otp: str

class InventoryItemCreate(BaseModel):
    name: str
    quantity: int
    unit: str
    min_threshold: int = 10 # ✅ Added this field

class InventoryUpdate(BaseModel):
    quantity: int

class TreatmentCreate(BaseModel):
    name: str
    cost: float
    description: str = ""

class TreatmentLinkCreate(BaseModel):
    item_id: int
    quantity: int

class BlockSlotCreate(BaseModel):
    date: str
    time: Optional[str] = None
    reason: str
    is_whole_day: bool = False

class PatientCreateByDoctor(BaseModel):
    full_name: str
    email: str
    age: int
    gender: str

class RecordCreate(BaseModel):
    diagnosis: str
    prescription: str
    notes: str = ""

class AppointmentCreate(BaseModel):
    doctor_id: int
    date: str
    time: str
    reason: str

class PatientProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    blood_group: Optional[str] = None

class UserProfileUpdate(BaseModel):
    full_name: str
    email: str
    phone_number: Optional[str] = None
    address: Optional[str] = None
    specialization: Optional[str] = None

class LocationUpdate(BaseModel):
    address: str
    pincode: str
    lat: float
    lng: float
