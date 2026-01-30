from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Float, Table
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String)
    is_active = Column(Boolean, default=True)

    doctor_profile = relationship("Doctor", back_populates="user", uselist=False)
    patient_profile = relationship("Patient", back_populates="user", uselist=False)

class Hospital(Base):
    __tablename__ = "hospitals"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    address = Column(String)
    contact_number = Column(String)
    
    # Relationships
    doctors = relationship("Doctor", back_populates="hospital")
    inventory = relationship("InventoryItem", back_populates="hospital")

class Doctor(Base):
    __tablename__ = "doctors"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    hospital_id = Column(Integer, ForeignKey("hospitals.id"))
    specialization = Column(String)
    
    user = relationship("User", back_populates="doctor_profile")
    hospital = relationship("Hospital", back_populates="doctors")
    appointments = relationship("Appointment", back_populates="doctor")
    treatments = relationship("Treatment", back_populates="doctor")

class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date_of_birth = Column(String)
    gender = Column(String)
    medical_history = Column(String)
    
    user = relationship("User", back_populates="patient_profile")
    appointments = relationship("Appointment", back_populates="patient")
    invoices = relationship("Invoice", back_populates="patient")
    prescriptions = relationship("Prescription", back_populates="patient")

class Appointment(Base):
    __tablename__ = "appointments"
    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    patient_id = Column(Integer, ForeignKey("patients.id"))
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
    patient_id = Column(Integer, ForeignKey("patients.id"))
    amount = Column(Float)
    status = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    details = Column(String)
    
    patient = relationship("Patient", back_populates="invoices")

class Prescription(Base):
    __tablename__ = "prescriptions"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    medication = Column(String)
    dosage = Column(String)
    instructions = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    patient = relationship("Patient", back_populates="prescriptions")

# --- INVENTORY & TREATMENTS (Clean Definitions) ---

class InventoryItem(Base):
    __tablename__ = "inventory_items"
    id = Column(Integer, primary_key=True, index=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"))
    name = Column(String, index=True)
    category = Column(String, nullable=True)
    quantity = Column(Integer, default=0)
    unit = Column(String, nullable=True)
    min_threshold = Column(Integer, default=10)
    last_updated = Column(DateTime, default=datetime.utcnow)

    hospital = relationship("Hospital", back_populates="inventory")

class Treatment(Base):
    __tablename__ = "treatments"
    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    name = Column(String, index=True)
    cost = Column(Float)
    description = Column(String, nullable=True)
    
    doctor = relationship("Doctor", back_populates="treatments")
