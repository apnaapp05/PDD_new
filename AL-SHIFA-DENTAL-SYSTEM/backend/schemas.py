from pydantic import BaseModel
from typing import Optional, List

class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str
    role: str
    age: Optional[int] = None
    gender: Optional[str] = None
    hospital_name: Optional[str] = None
    specialization: Optional[str] = None
    license_number: Optional[str] = None
    address: Optional[str] = None

class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
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
    license_number: Optional[str] = None

class LocationUpdate(BaseModel):
    address: str
    pincode: str
    lat: float
    lng: float
