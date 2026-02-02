from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String)
    phone_number = Column(String, nullable=True) # Added for profile updates
    address = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_email_verified = Column(Boolean, default=False)
    otp_code = Column(String, nullable=True)
    otp_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Organization(Base):
    __tablename__ = "organizations"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    address = Column(String)
    is_verified = Column(Boolean, default=False)
    user = relationship("User")

class Hospital(Base): # Alias for Organization to match main.py logic
    __tablename__ = "hospitals"
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    address = Column(String)
    is_verified = Column(Boolean, default=False)
    # Pending location changes
    pending_address = Column(String, nullable=True)
    pending_pincode = Column(String, nullable=True)
    pending_lat = Column(Float, nullable=True)
    pending_lng = Column(Float, nullable=True)
    
    owner = relationship("User")
    doctors = relationship("Doctor", back_populates="hospital")

class Doctor(Base):
    __tablename__ = "doctors"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    hospital_id = Column(Integer, ForeignKey("hospitals.id"))
    specialization = Column(String)
    experience = Column(Integer)
    license_number = Column(String) # ✅ Added License Number
    is_verified = Column(Boolean, default=False)
    scheduling_config = Column(Text, nullable=True) # JSON string
    
    user = relationship("User")
    hospital = relationship("Hospital", back_populates="doctors")

class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    age = Column(Integer)
    gender = Column(String)
    blood_group = Column(String, nullable=True)
    user = relationship("User")

class Treatment(Base):
    __tablename__ = "treatments"
    id = Column(Integer, primary_key=True, index=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"))
    doctor_id = Column(Integer, ForeignKey("doctors.id")) # Optional ownership
    name = Column(String)
    description = Column(String)
    cost = Column(Float)
    required_items = relationship("TreatmentInventoryLink", back_populates="treatment")

class InventoryItem(Base):
    __tablename__ = "inventory"
    id = Column(Integer, primary_key=True, index=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"))
    name = Column(String)
    quantity = Column(Integer)
    unit = Column(String)
    min_threshold = Column(Integer, default=10) # ✅ Fixed Name
    buying_cost = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=datetime.utcnow)

class TreatmentInventoryLink(Base):
    __tablename__ = "treatment_inventory_links"
    id = Column(Integer, primary_key=True, index=True)
    treatment_id = Column(Integer, ForeignKey("treatments.id"))
    item_id = Column(Integer, ForeignKey("inventory.id"))
    quantity_required = Column(Integer)
    
    treatment = relationship("Treatment", back_populates="required_items")
    item = relationship("InventoryItem")

class Appointment(Base):
    __tablename__ = "appointments"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True) # Nullable for blocked slots
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    treatment_type = Column(String)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    status = Column(String, default="pending") 
    notes = Column(Text, nullable=True)

    patient = relationship("Patient")
    doctor = relationship("Doctor")
    invoices = relationship("Invoice", back_populates="appointment")

class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"))
    patient_id = Column(Integer, ForeignKey("patients.id"))
    amount = Column(Float)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

    appointment = relationship("Appointment", back_populates="invoices")
    patient = relationship("Patient")

class MedicalRecord(Base):
    __tablename__ = "medical_records"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    diagnosis = Column(String)
    prescription = Column(Text)
    notes = Column(Text)
    date = Column(DateTime, default=datetime.utcnow)
    
    doctor = relationship("Doctor")
    patient = relationship("Patient")

class PatientFile(Base):
    __tablename__ = "patient_files"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    filename = Column(String)
    filepath = Column(String)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

