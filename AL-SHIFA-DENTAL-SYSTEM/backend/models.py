from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)  # FIXED: Standardized to password_hash
    role = Column(String)
    is_active = Column(Boolean, default=True)
    
    # Extra fields for verification/profile
    is_email_verified = Column(Boolean, default=False)
    phone_number = Column(String, nullable=True)
    address = Column(String, nullable=True)
    otp_code = Column(String, nullable=True)
    otp_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    doctor_profile = relationship("Doctor", back_populates="user", uselist=False)
    patient_profile = relationship("Patient", back_populates="user", uselist=False)

class Hospital(Base):
    __tablename__ = "hospitals"
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id")) # Link to Organization User
    name = Column(String, unique=True, index=True)
    address = Column(String)
    contact_number = Column(String)
    phone_number = Column(String, nullable=True)
    is_verified = Column(Boolean, default=False)
    
    # Location request fields
    pending_address = Column(String, nullable=True)
    pending_lat = Column(Float, nullable=True)
    pending_lng = Column(Float, nullable=True)
    pending_pincode = Column(String, nullable=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)

    owner = relationship("User")
    doctors = relationship("Doctor", back_populates="hospital")
    inventory = relationship("InventoryItem", back_populates="hospital")

class Doctor(Base):
    __tablename__ = "doctors"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=True)
    specialization = Column(String)
    license_number = Column(String, nullable=True)
    is_verified = Column(Boolean, default=False)
    scheduling_config = Column(String, nullable=True)
    
    user = relationship("User", back_populates="doctor_profile")
    hospital = relationship("Hospital", back_populates="doctors")
    appointments = relationship("Appointment", back_populates="doctor")
    treatments = relationship("Treatment", back_populates="doctor")

class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)
    medical_history = Column(String, nullable=True)
    blood_group = Column(String, nullable=True)
    
    user = relationship("User", back_populates="patient_profile")
    appointments = relationship("Appointment", back_populates="patient")
    invoices = relationship("Invoice", back_populates="patient")
    prescriptions = relationship("Prescription", back_populates="patient")

class Appointment(Base):
    __tablename__ = "appointments"
    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    status = Column(String, default="pending")
    notes = Column(String, nullable=True)
    treatment_type = Column(String, nullable=True)
    
    doctor = relationship("Doctor", back_populates="appointments")
    patient = relationship("Patient", back_populates="appointments")

class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    amount = Column(Float)
    status = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    details = Column(String, nullable=True)
    
    patient = relationship("Patient", back_populates="invoices")
    appointment = relationship("Appointment")

class Prescription(Base):
    __tablename__ = "prescriptions"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    medication = Column(String)
    dosage = Column(String)
    instructions = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    patient = relationship("Patient", back_populates="prescriptions")

class InventoryItem(Base):
    __tablename__ = "inventory_items"
    id = Column(Integer, primary_key=True, index=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"))
    name = Column(String, index=True)
    category = Column(String, nullable=True)
    quantity = Column(Integer, default=0)
    unit = Column(String, nullable=True)
    threshold = Column(Integer, default=10)
    last_updated = Column(DateTime, default=datetime.utcnow)

    hospital = relationship("Hospital", back_populates="inventory")

class Treatment(Base):
    __tablename__ = "treatments"
    id = Column(Integer, primary_key=True, index=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"))
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=True)
    name = Column(String, index=True)
    cost = Column(Float)
    description = Column(String, nullable=True)
    
    doctor = relationship("Doctor", back_populates="treatments")
    required_items = relationship("TreatmentInventoryLink", back_populates="treatment")

class MedicalRecord(Base):
    __tablename__ = "medical_records"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    diagnosis = Column(String)
    prescription = Column(String)
    notes = Column(String, nullable=True)
    date = Column(DateTime, default=datetime.utcnow)
    
    patient = relationship("Patient")
    doctor = relationship("Doctor")

class PatientFile(Base):
    __tablename__ = "patient_files"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    filename = Column(String)
    filepath = Column(String)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

class TreatmentInventoryLink(Base):
    __tablename__ = "treatment_inventory_links"
    treatment_id = Column(Integer, ForeignKey("treatments.id"), primary_key=True)
    item_id = Column(Integer, ForeignKey("inventory_items.id"), primary_key=True)
    quantity_required = Column(Integer)
    
    treatment = relationship("Treatment", back_populates="required_items")
    item = relationship("InventoryItem")
