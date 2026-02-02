from services.analytics_service import AnalyticsService
import csv
import codecs
import logging
import os
import shutil
import json
import random
import string
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI, Depends, HTTPException, status, APIRouter, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from jose import jwt, JWTError
import bcrypt

import models
import database
import schemas
import config
from notifications.email import EmailAdapter
import agent_routes

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIG ---
SECRET_KEY = config.SECRET_KEY
ALGORITHM = config.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = config.ACCESS_TOKEN_EXPIRE_MINUTES

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

try:
    email_service = EmailAdapter()
except Exception as e:
    logger.warning(f"Email service failed to initialize: {e}")
    email_service = None

# --- DATABASE & STARTUP ---
def init_db():
    models.Base.metadata.create_all(bind=database.engine)

def create_default_admin(db: Session):
    admin_email = config.ADMIN_EMAIL
    new_password = config.ADMIN_PASSWORD
    
    user = db.query(models.User).filter(models.User.email == admin_email).first()
    if not user:
        pwd_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        db.add(models.User(
            email=admin_email, 
            full_name="System Admin", 
            role="admin", 
            is_email_verified=True, 
            password_hash=pwd_hash,
            phone_number="000-000-0000",
            address="Admin HQ"
        ))
        db.commit()
        print(f"✅ [Startup] Admin account created: {admin_email}")
    else:
        user.password_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        db.commit()
        print(f"✅ [Startup] Admin password synced.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    db = database.SessionLocal()
    try:
        create_default_admin(db)
    finally:
        db.close()
    yield

# --- APP INITIALIZATION ---
app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# --- UTILS ---
def get_db():
    db = database.SessionLocal()
    try: yield db
    finally: db.close()

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

def create_access_token(data: dict):
    to_encode = data.copy()
    to_encode.update({"exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def generate_otp():
    return "".join(random.choices(string.digits, k=6))

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None: raise HTTPException(401, "Invalid token")
    except JWTError: raise HTTPException(401, "Invalid token")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None: raise HTTPException(401, "User not found")
    return user

# --- EMAIL TEMPLATES ---
def get_otp_email_template(name: str, otp: str):
    plain_text = f"Subject: Your Code - Al-Shifa\nDear {name},\nCode: {otp}"
    html_content = f"<h1>Verify Account</h1><p>Dear {name},</p><h3>{otp}</h3>"
    return plain_text, html_content

# --- ROUTERS ---
auth_router = APIRouter(prefix="/auth", tags=["Auth"])
admin_router = APIRouter(prefix="/admin", tags=["Admin"])
org_router = APIRouter(prefix="/organization", tags=["Organization"])
doctor_router = APIRouter(prefix="/doctor", tags=["Doctor"])
public_router = APIRouter(tags=["Public"]) 

# ================= PUBLIC ROUTES =================
@public_router.get("/")
def health_check():
    return {"status": "running", "system": "Al-Shifa Dental API"}

@public_router.get("/doctors")
def get_public_doctors(db: Session = Depends(get_db)):
    doctors = db.query(models.Doctor).filter(models.Doctor.is_verified == True).all()
    results = []
    for d in doctors:
        hospital = d.hospital
        user = d.user
        results.append({
            "id": d.id,
            "full_name": user.full_name if user else "Unknown",
            "specialization": d.specialization,
            "hospital_id": hospital.id if hospital else None,
            "hospital_name": hospital.name if hospital else "Unknown",
            "location": hospital.address if hospital else "Unknown"
        })
    return results

@public_router.get("/doctors/{doctor_id}/treatments")
def get_doctor_treatments_public(doctor_id: int, db: Session = Depends(get_db)):
    doctor = db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()
    if not doctor: return []
    treatments = db.query(models.Treatment).filter(models.Treatment.doctor_id == doctor.id).all()
    if not treatments and doctor.hospital_id:
         treatments = db.query(models.Treatment).filter(
             models.Treatment.hospital_id == doctor.hospital_id,
             models.Treatment.doctor_id == None 
         ).all()

    return [{"name": t.name, "cost": t.cost, "description": t.description} for t in treatments]

@public_router.get("/doctors/{doctor_id}/settings")
def get_public_doctor_settings(doctor_id: int, db: Session = Depends(get_db)):
    doc = db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()
    if not doc: raise HTTPException(404, "Doctor not found")
    default_settings = {"work_start_time": "09:00", "work_end_time": "17:00", "slot_duration": 30}
    if not doc.scheduling_config: return default_settings
    try: return json.loads(doc.scheduling_config)
    except: return default_settings


@public_router.get("/doctors/{doctor_id}/booked-slots")
def get_booked_slots_public(doctor_id: int, date: str, db: Session = Depends(get_db)):
    """Returns a list of ALL 30-min slots that are occupied"""
    try:
        query_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(400, "Invalid date format")

    start_of_day = datetime.combine(query_date, datetime.min.time())
    end_of_day = datetime.combine(query_date, datetime.max.time())

    appts = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == doctor_id,
        models.Appointment.start_time < end_of_day, 
        models.Appointment.end_time > start_of_day,
        models.Appointment.status.in_(["confirmed", "pending", "checked-in", "in_progress", "blocked"])
    ).all()

    occupied_slots = []
    
    for a in appts:
        start = max(a.start_time, start_of_day)
        end = min(a.end_time, end_of_day)
        
        curr = start
        while curr < end:
            slot_str = curr.strftime("%I:%M %p")
            occupied_slots.append(slot_str)
            curr += timedelta(minutes=30)
            
    return list(set(occupied_slots)) 

@public_router.post("/appointments")
def create_appointment(appt: schemas.AppointmentCreate, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "patient": raise HTTPException(403, "Only patients can book")
    patient = db.query(models.Patient).filter(models.Patient.user_id == user.id).first()
    if not patient: raise HTTPException(400, "Patient profile not found")
    
    try: start_dt = datetime.strptime(f"{appt.date} {appt.time}", "%Y-%m-%d %I:%M %p")
    except:
        try: start_dt = datetime.strptime(f"{appt.date} {appt.time}", "%Y-%m-%d %H:%M")
        except: raise HTTPException(400, "Invalid date/time format")
    
    if start_dt < datetime.now(): raise HTTPException(400, "Cannot book past time")
    
    active_appt = db.query(models.Appointment).filter(
        models.Appointment.patient_id == patient.id,
        models.Appointment.status.in_(["confirmed", "pending", "checked-in", "in_progress"])
    ).first()
    
    if active_appt:
        raise HTTPException(400, f"You already have an active appointment on {active_appt.start_time.strftime('%Y-%m-%d')}. Please cancel or reschedule it first.")

    end_dt = start_dt + timedelta(minutes=30)

    existing = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == appt.doctor_id,
        models.Appointment.status.in_(["confirmed", "blocked", "in_progress"]),
        models.Appointment.start_time < end_dt,
        models.Appointment.end_time > start_dt
    ).first()
    if existing: raise HTTPException(400, "Slot unavailable")

    new_appt = models.Appointment(
        doctor_id=appt.doctor_id,
        patient_id=patient.id,
        start_time=start_dt,
        end_time=end_dt,
        status="confirmed",
        treatment_type=appt.reason,
        notes="Booked via Portal"
    )
    db.add(new_appt); db.flush()

    doc = db.query(models.Doctor).filter(models.Doctor.id == appt.doctor_id).first()
    if doc:
        treatment = db.query(models.Treatment).filter(models.Treatment.hospital_id == doc.hospital_id, models.Treatment.name == appt.reason).first()
        amount = treatment.cost if treatment else 0
        db.add(models.Invoice(appointment_id=new_appt.id, patient_id=patient.id, amount=amount, status="pending"))

    db.commit(); db.refresh(new_appt)
    return {"message": "Booked", "id": new_appt.id}

@public_router.get("/patient/appointments")
def get_my_appointments(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = db.query(models.Patient).filter(models.Patient.user_id == user.id).first()
    if not p: return []
    appts = db.query(models.Appointment).filter(models.Appointment.patient_id == p.id, models.Appointment.status != "cancelled").order_by(models.Appointment.start_time.desc()).all()
    res = []
    for a in appts:
        d = db.query(models.Doctor).filter(models.Doctor.id == a.doctor_id).first()
        res.append({
            "id": a.id, "treatment": a.treatment_type, "doctor": d.user.full_name if d else "Unknown",
            "date": a.start_time.strftime("%Y-%m-%d"), "time": a.start_time.strftime("%I:%M %p"),
            "status": a.status, "hospital_name": d.hospital.name if d and d.hospital else ""
        })
    return res

@public_router.put("/patient/appointments/{appt_id}/cancel")
def cancel_patient_appointment(appt_id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = db.query(models.Patient).filter(models.Patient.user_id == user.id).first()
    if not p: raise HTTPException(404, "Patient not found")
    appt = db.query(models.Appointment).filter(models.Appointment.id == appt_id, models.Appointment.patient_id == p.id).first()
    if not appt: raise HTTPException(404, "Appointment not found")
    appt.status = "cancelled"
    inv = db.query(models.Invoice).filter(models.Invoice.appointment_id == appt.id, models.Invoice.status == "pending").first()
    if inv: inv.status = "cancelled"
    db.commit()
    return {"message": "Cancelled"}

@public_router.get("/patient/invoices")
def get_my_invoices(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = db.query(models.Patient).filter(models.Patient.user_id == user.id).first()
    if not p: return []
    invoices = db.query(models.Invoice).filter(models.Invoice.patient_id == p.id).order_by(models.Invoice.created_at.desc()).all()
    res = []
    for i in invoices:
        appt = i.appointment
        doc = appt.doctor if appt else None
        res.append({
            "id": i.id, "amount": i.amount, "status": i.status, "date": i.created_at.strftime("%Y-%m-%d"),
            "treatment": appt.treatment_type if appt else "N/A",
            "doctor_name": doc.user.full_name if doc and doc.user else "Unknown"
        })
    return res

@public_router.get("/patient/invoices/{id}")
def get_patient_invoice_detail(id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = db.query(models.Patient).filter(models.Patient.user_id == user.id).first()
    inv = db.query(models.Invoice).filter(models.Invoice.id == id, models.Invoice.patient_id == p.id).first()
    if not inv: raise HTTPException(404)
    appt = inv.appointment
    return {
        "id": inv.id, "date": str(inv.created_at), "amount": inv.amount, "status": inv.status,
        "hospital": {"name": appt.doctor.hospital.name, "address": appt.doctor.hospital.address, "phone": appt.doctor.hospital.owner.phone_number or ""},
        "doctor": {"name": appt.doctor.user.full_name},
        "patient": {"name": user.full_name, "id": p.id},
        "treatment": {"name": appt.treatment_type}
    }

@public_router.get("/patient/records")
def get_my_records(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = db.query(models.Patient).filter(models.Patient.user_id == user.id).first()
    if not p: return []
    recs = db.query(models.MedicalRecord).filter(models.MedicalRecord.patient_id == p.id).order_by(models.MedicalRecord.date.desc()).all()
    return [{"id": r.id, "diagnosis": r.diagnosis, "prescription": r.prescription, "date": r.date.strftime("%Y-%m-%d"), "doctor_name": r.doctor.user.full_name} for r in recs]

@public_router.get("/patient/profile")
def get_patient_profile(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "patient": raise HTTPException(403)
    p = db.query(models.Patient).filter(models.Patient.user_id == user.id).first()
    if not p: raise HTTPException(404, "Patient profile not found")
    return {
        "id": p.id, "full_name": user.full_name, "email": user.email,
        "age": p.age, "gender": p.gender, "address": user.address or "", 
        "blood_group": getattr(p, "blood_group", "")
    }

@public_router.put("/patient/profile")
def update_patient_profile(data: schemas.PatientProfileUpdate, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "patient": raise HTTPException(403, "Access denied")
    if data.full_name: user.full_name = data.full_name
    if data.address is not None: user.address = data.address
    p = db.query(models.Patient).filter(models.Patient.user_id == user.id).first()
    if not p: raise HTTPException(404, "Patient profile not found")
    if data.age is not None: p.age = data.age
    if data.gender: p.gender = data.gender
    if data.blood_group: p.blood_group = data.blood_group
    db.commit()
    return {"message": "Profile updated successfully"}

# ================= DOCTOR ROUTES =================

@doctor_router.put("/inventory/{item_id}")
def update_inventory_item(item_id: int, data: schemas.InventoryUpdate, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "doctor": raise HTTPException(403)
    doctor = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
    item = db.query(models.InventoryItem).filter(models.InventoryItem.id == item_id, models.InventoryItem.hospital_id == doctor.hospital_id).first()
    if not item: raise HTTPException(404)
    item.quantity = data.quantity; item.last_updated = datetime.utcnow()
    db.commit()
    return {"message": "Updated", "new_quantity": item.quantity}

@doctor_router.get("/dashboard")
def get_doctor_dashboard(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
    if not doc: return {"account_status": "no_profile"}
    
    now = datetime.now()
    appts = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == doc.id,
        models.Appointment.start_time >= now.replace(hour=0, minute=0, second=0),
        models.Appointment.start_time < now.replace(hour=0, minute=0, second=0) + timedelta(days=1),
        models.Appointment.status != "cancelled"
    ).order_by(models.Appointment.start_time).all()
    
    revenue = db.query(func.sum(models.Invoice.amount)).join(models.Appointment).filter(models.Appointment.doctor_id == doc.id, models.Invoice.status == "paid").scalar() or 0
    total_patients = db.query(models.Appointment.patient_id).filter(models.Appointment.doctor_id == doc.id).distinct().count()
    
    analysis = {}
    analysis["queue"] = f"{len(appts)} patients today."
    low_stock = db.query(models.InventoryItem).filter(models.InventoryItem.hospital_id == doc.hospital_id, models.InventoryItem.quantity < models.InventoryItem.min_threshold).count()
    analysis["inventory"] = f"{low_stock} items low." if low_stock else "Inventory OK."
    analysis["revenue"] = f"Rev: Rs. {revenue}"

    appt_list = []
    for a in appts:
        p = db.query(models.Patient).filter(models.Patient.id == a.patient_id).first()
        appt_list.append({
            "id": a.id, "patient_name": p.user.full_name if p else "Unknown", 
            "treatment": a.treatment_type, "time": a.start_time.strftime("%I:%M %p"), "status": a.status
        })

    return {
        "account_status": "active", "doctor_name": user.full_name,
        "today_count": len(appts), "total_patients": total_patients, "revenue": revenue,
        "appointments": appt_list, "analysis": analysis
    }

@doctor_router.post("/appointments/{id}/start")
def start_appointment(id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
    appt = db.query(models.Appointment).filter(models.Appointment.id == id, models.Appointment.doctor_id == doc.id).first()
    if not appt: raise HTTPException(404)
    appt.status = "in_progress"; db.commit()
    return {"message": "Started", "status": "in_progress"}

@doctor_router.post("/appointments/{id}/complete")
def complete_appointment(id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
    appt = db.query(models.Appointment).filter(models.Appointment.id == id, models.Appointment.doctor_id == doc.id).first()
    if not appt: raise HTTPException(404)
    if appt.status == "completed": return {"message": "Already completed"}
    
    inv = db.query(models.Invoice).filter(models.Invoice.appointment_id == appt.id).first()
    if inv: inv.status = "paid"
    else:
        t = db.query(models.Treatment).filter(models.Treatment.name == appt.treatment_type, models.Treatment.hospital_id == doc.hospital_id).first()
        db.add(models.Invoice(appointment_id=appt.id, patient_id=appt.patient_id, amount=t.cost if t else 0, status="paid"))

    # DEDUCT STOCK BASED ON RECIPE
    t = db.query(models.Treatment).filter(models.Treatment.name == appt.treatment_type, models.Treatment.hospital_id == doc.hospital_id).first()
    if t:
        for l in t.required_items:
             if l.item:
                l.item.quantity = max(0, l.item.quantity - l.quantity_required)
    
    appt.status = "completed"; db.commit()
    return {"message": "Completed", "status": "completed"}

@doctor_router.post("/treatments/upload")
@app.post("/api/treatments/upload")
async def upload_treatments(file: UploadFile = File(...), user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "doctor": raise HTTPException(403)
    doctor = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
    try:
        content = await file.read()
        decoded = content.decode("utf-8-sig").splitlines()
        csvReader = csv.DictReader(decoded)
        count = 0
        for row in csvReader:
            data = {k.lower().strip(): v.strip() for k, v in row.items() if k}
            name = data.get("treatment name") or data.get("name")
            cost_str = data.get("cost") or data.get("price")
            desc = data.get("description") or ""
            if not name or not cost_str: continue
            try: cost = float(cost_str)
            except: continue
            existing = db.query(models.Treatment).filter(models.Treatment.doctor_id == doctor.id, models.Treatment.name == name).first()
            if existing: existing.cost = cost
            else: db.add(models.Treatment(hospital_id=doctor.hospital_id, doctor_id=doctor.id, name=name, cost=cost, description=desc))
            count += 1
        db.commit(); return {"message": f"Uploaded {count} treatments"}
    except Exception as e: db.rollback(); raise HTTPException(400, f"Error: {str(e)}")

@doctor_router.post("/inventory/upload")
@app.post("/api/inventory/upload")
async def upload_inventory(
    file: UploadFile = File(...), 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a CSV.")

    content = await file.read()
    decoded = content.decode("utf-8-sig").splitlines()
    reader = csv.DictReader(decoded)

    headers = [h.lower().strip() for h in reader.fieldnames] if reader.fieldnames else []
    
    if not any("name" in h for h in headers) or not any("qty" in h or "quantity" in h for h in headers):
        return JSONResponse(status_code=400, content={"detail": "CSV must have 'Item Name' and 'Quantity' columns."})

    doc = db.query(models.Doctor).filter(models.Doctor.user_id == current_user.id).first()
    hid = doc.hospital_id if doc else 1
    
    count = 0
    updated = 0

    try:
        for row in reader:
            row = {k.lower().strip(): v for k, v in row.items()}
            
            name = row.get("item name") or row.get("name")
            if not name: continue
            
            qty = int(row.get("quantity") or row.get("qty") or 0)
            unit = row.get("unit") or "Pcs"
            threshold = int(row.get("min threshold") or row.get("min") or row.get("threshold") or 10)

            existing = db.query(models.InventoryItem).filter(
                models.InventoryItem.hospital_id == hid, 
                models.InventoryItem.name == name
            ).first()
            
            if existing:
                existing.quantity = qty
                existing.unit = unit
                existing.min_threshold = threshold
                updated += 1
            else:
                new_item = models.InventoryItem(
                    hospital_id=hid,
                    name=name,
                    quantity=qty,
                    unit=unit,
                    min_threshold=threshold
                )
                db.add(new_item)
                count += 1
        
        db.commit()
        return {"message": f"✅ Upload Complete: {count} new, {updated} updated."}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Row Error: {str(e)}")

@doctor_router.get("/treatments")
def get_doc_treatments(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
    treatments = db.query(models.Treatment).filter(models.Treatment.doctor_id == doc.id).all()
    results = []
    for t in treatments:
        recipe = [{"item_name": l.item.name, "qty_required": l.quantity_required, "unit": l.item.unit} for l in t.required_items]
        results.append({"id": t.id, "name": t.name, "cost": t.cost, "description": t.description, "recipe": recipe})
    return results

@doctor_router.post("/treatments")
def create_treatment(data: schemas.TreatmentCreate, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
    
    if db.query(models.Treatment).filter(models.Treatment.doctor_id == doc.id, models.Treatment.name == data.name).first():
        raise HTTPException(400, "Treatment already exists")

    db.add(models.Treatment(hospital_id=doc.hospital_id, doctor_id=doc.id, name=data.name, cost=data.cost, description=data.description))
    db.commit()
    return {"message": "Created"}

@doctor_router.post("/treatments/{tid}/link-inventory")
def link_inv(tid: int, data: schemas.TreatmentLinkCreate, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    link = db.query(models.TreatmentInventoryLink).filter(models.TreatmentInventoryLink.treatment_id == tid, models.TreatmentInventoryLink.item_id == data.item_id).first()
    if link: link.quantity_required = data.quantity
    else: db.add(models.TreatmentInventoryLink(treatment_id=tid, item_id=data.item_id, quantity_required=data.quantity))
    db.commit(); return {"message": "Linked"}

@doctor_router.get("/inventory")
def get_inv(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
    items = db.query(models.InventoryItem).filter(models.InventoryItem.hospital_id == doc.hospital_id).all()
    return [{
        "id": i.id, 
        "name": i.name, 
        "quantity": i.quantity, 
        "unit": i.unit, 
        "min_threshold": i.min_threshold, 
        "last_updated": i.last_updated.isoformat() if i.last_updated else None
    } for i in items]

@doctor_router.post("/inventory")
def add_inv(item: schemas.InventoryItemCreate, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
    db.add(models.InventoryItem(hospital_id=doc.hospital_id, name=item.name, quantity=item.quantity, unit=item.unit, min_threshold=item.min_threshold))
    db.commit(); return {"message": "Added"}

@doctor_router.get("/schedule")
def get_sched(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
    return db.query(models.Appointment).filter(
        models.Appointment.doctor_id == doc.id,
        models.Appointment.status != "cancelled" 
    ).all()

@doctor_router.get("/appointments")
def get_daily_appointments(date: str, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "doctor": raise HTTPException(403)
    doc = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
    try:
        query_date = datetime.strptime(date, "%Y-%m-%d")
        start_of_day = query_date.replace(hour=0, minute=0, second=0)
        end_of_day = query_date.replace(hour=23, minute=59, second=59)
    except: raise HTTPException(400, "Invalid date format. Use YYYY-MM-DD")

    appts = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == doc.id,
        models.Appointment.start_time >= start_of_day,
        models.Appointment.start_time <= end_of_day,
        models.Appointment.status != "cancelled"
    ).all()
    
    res = []
    for a in appts:
        p_name = "Blocked Slot"
        if a.patient_id:
            p = db.query(models.Patient).filter(models.Patient.id == a.patient_id).first()
            p_name = p.user.full_name if p else "Unknown"
        elif a.status == "blocked": p_name = a.notes or "Blocked"

        res.append({
            "id": a.id, "patient_name": p_name,
            "start": a.start_time.isoformat(), "end": a.end_time.isoformat(),
            "status": a.status, "treatment": a.treatment_type
        })
    return {"appointments": res}

@doctor_router.post("/schedule/block")
def block_slot(data: schemas.BlockSlotCreate, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "doctor": raise HTTPException(403)
    doc = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
    
    start_dt = datetime.strptime(f"{data.date} {data.time or '00:00'}", "%Y-%m-%d %H:%M")
    end_dt = start_dt + timedelta(minutes=30) 
    if data.is_whole_day: end_dt = start_dt + timedelta(days=1)
        
    db.add(models.Appointment(doctor_id=doc.id, patient_id=None, start_time=start_dt, end_time=end_dt, status="blocked", notes=data.reason))
    db.commit(); return {"message": "Blocked"}

@doctor_router.get("/schedule/settings")
def get_schedule_settings(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "doctor": raise HTTPException(403)
    doc = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
    if not doc.scheduling_config: return {"work_start_time": "09:00", "work_end_time": "17:00", "slot_duration": 30}
    try: return json.loads(doc.scheduling_config)
    except: return {"work_start_time": "09:00", "work_end_time": "17:00", "slot_duration": 30}

@doctor_router.put("/schedule/settings")
def update_schedule_settings(settings: dict, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "doctor": raise HTTPException(403)
    doc = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
    doc.scheduling_config = json.dumps(settings)
    db.commit()
    return {"message": "Settings updated"}

@doctor_router.get("/finance")
def get_fin(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
    if not doc: return {"total_revenue": 0, "total_pending": 0, "invoices": []}
    
    try:
        service = AnalyticsService(db, doc.id)
        data = service.get_financial_summary()
        return {
            "total_revenue": data["revenue"],
            "total_pending": data["pending"],
            "invoices": data["invoices"]
        }
    except Exception as e:
        print(f"Finance Error: {e}")
        return {"total_revenue": 0, "total_pending": 0, "invoices": []}

@doctor_router.get("/patients")
def get_doc_patients(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
    appts = db.query(models.Appointment).filter(models.Appointment.doctor_id == doc.id).all()
    pids = set(a.patient_id for a in appts)
    recs = db.query(models.MedicalRecord).filter(models.MedicalRecord.doctor_id == doc.id).all()
    pids.update(r.patient_id for r in recs)
    
    res = []
    for pid in pids:
        if pid is None: continue
        p = db.query(models.Patient).filter(models.Patient.id == pid).first()
        if p:
             last_appt = db.query(models.Appointment).filter(models.Appointment.patient_id == p.id, models.Appointment.doctor_id == doc.id).order_by(models.Appointment.start_time.desc()).first()
             last_visit = last_appt.start_time.strftime("%Y-%m-%d") if last_appt else "N/A"
             res.append({"id": p.id, "name": p.user.full_name, "age": p.age, "gender": p.gender, "last_visit": last_visit, "status": "Active", "condition": "Checkup"})
    return res

@doctor_router.post("/patients")
def create_patient_by_doctor(data: schemas.PatientCreateByDoctor, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "doctor": raise HTTPException(403)
    if db.query(models.User).filter(models.User.email == data.email).first(): raise HTTPException(400, "Email already registered")
    
    pwd = get_password_hash("123456") 
    new_user = models.User(email=data.email, password_hash=pwd, full_name=data.full_name, role="patient", is_email_verified=True)
    db.add(new_user); db.flush()
    new_patient = models.Patient(user_id=new_user.id, age=data.age, gender=data.gender)
    db.add(new_patient); db.commit()
    
    doc = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
    db.add(models.MedicalRecord(patient_id=new_patient.id, doctor_id=doc.id, diagnosis="New Patient Registration", prescription="", notes="Registered by Doctor"))
    db.commit()
    return {"message": "Patient created", "id": new_patient.id}

@doctor_router.get("/patients/{id}")
def get_pat_det(id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = db.query(models.Patient).filter(models.Patient.id == id).first()
    if not p: raise HTTPException(404, "Patient not found")
    recs = db.query(models.MedicalRecord).filter(models.MedicalRecord.patient_id == id).all()
    files = db.query(models.PatientFile).filter(models.PatientFile.patient_id == id).all()
    return {"id": p.id, "full_name": p.user.full_name, "age": p.age, "gender": p.gender, 
            "history": [{"date": r.date.strftime("%Y-%m-%d"), "diagnosis": r.diagnosis, "prescription": r.prescription, "doctor_name": r.doctor.user.full_name} for r in recs],
            "files": [{"id": f.id, "filename": f.filename, "path": f.filepath, "date": f.uploaded_at.strftime("%Y-%m-%d")} for f in files]}

@doctor_router.post("/patients/{patient_id}/files")
def upload_patient_file(patient_id: int, file: UploadFile = File(...), user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "doctor": raise HTTPException(403, "Access denied")
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient: raise HTTPException(404, "Patient not found")
    os.makedirs("media", exist_ok=True)
    file_location = f"media/{patient_id}_{file.filename}"
    with open(file_location, "wb") as buffer: shutil.copyfileobj(file.file, buffer)
    db.add(models.PatientFile(patient_id=patient_id, filename=file.filename, filepath=file_location))
    db.commit()
    return {"message": "File uploaded successfully"}

@doctor_router.post("/patients/{id}/records")
def add_rec(id: int, data: schemas.RecordCreate, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
    db.add(models.MedicalRecord(patient_id=id, doctor_id=doc.id, diagnosis=data.diagnosis, prescription=data.prescription, notes=data.notes, date=datetime.utcnow()))
    db.commit(); return {"message": "Saved"}

@auth_router.post("/login")
def login(f: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    u = db.query(models.User).filter(models.User.email == f.username.lower().strip()).first()
    if not u or not verify_password(f.password, u.password_hash): raise HTTPException(403, "Invalid Credentials")
    if not u.is_email_verified: raise HTTPException(403, "Email not verified")
    
    if u.role == "doctor":
        d = db.query(models.Doctor).filter(models.Doctor.user_id == u.id).first()
        if d and not d.is_verified: raise HTTPException(403, "Account pending Admin approval")
    elif u.role == "organization":
        h = db.query(models.Hospital).filter(models.Hospital.owner_id == u.id).first()
        if h and not h.is_verified: raise HTTPException(403, "Account pending Admin approval")

    return {"access_token": create_access_token({"sub": str(u.id), "role": u.role}), "token_type": "bearer", "role": u.role}

@auth_router.post("/register")
def register(user: schemas.UserCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    email_clean = user.email.lower().strip()
    if db.query(models.User).filter(models.User.email == email_clean, models.User.is_email_verified == True).first(): 
        raise HTTPException(400, "Email already registered")
    
    existing_unverified = db.query(models.User).filter(models.User.email == email_clean, models.User.is_email_verified == False).first()
    otp = generate_otp()
    expires_at = datetime.utcnow() + timedelta(minutes=10)

    def send_email_safe(email, name, otp_code):
        if email_service:
            try:
                txt_msg, html_msg = get_otp_email_template(name, otp_code)
                email_service.send(to_email=email, subject="Verify your Account - Al-Shifa Dental", body=txt_msg, html_body=html_msg)
            except Exception as e: logger.error(f"Failed to send email to {email}: {e}")
        else: logger.info(f"EMAIL SERVICE NOT CONFIGURED. OTP for {email}: {otp_code}")

    try:
        if existing_unverified:
            existing_unverified.otp_code = otp
            existing_unverified.otp_expires_at = expires_at
            existing_unverified.password_hash = get_password_hash(user.password)
            existing_unverified.full_name = user.full_name
            db.commit()
        else:
            hashed_pw = get_password_hash(user.password)
            new_user = models.User(email=email_clean, password_hash=hashed_pw, full_name=user.full_name, role=user.role, is_email_verified=False, otp_code=otp, otp_expires_at=expires_at, address=user.address)
            db.add(new_user); db.flush() 
            if user.role == "organization": db.add(models.Hospital(owner_id=new_user.id, name=user.full_name, address=user.address or "Pending", is_verified=False))
            elif user.role == "patient": db.add(models.Patient(user_id=new_user.id, age=user.age or 0, gender=user.gender))
            elif user.role == "doctor":
                if not user.hospital_name: db.rollback(); raise HTTPException(400, "Hospital name required")
                hospital = db.query(models.Hospital).filter(models.Hospital.name == user.hospital_name).first()
                if not hospital: db.rollback(); raise HTTPException(400, "Hospital not found")
                db.add(models.Doctor(user_id=new_user.id, hospital_id=hospital.id, specialization=user.specialization, license_number=user.license_number, is_verified=False))
            db.commit()
        
        background_tasks.add_task(send_email_safe, email_clean, user.full_name, otp)
        return {"message": "OTP sent", "email": email_clean}
    except Exception as e: db.rollback(); raise HTTPException(500, f"Error: {str(e)}")

@auth_router.post("/verify-otp")
def verify_otp(data: schemas.VerifyOTP, db: Session = Depends(get_db)):
    email_clean = data.email.lower().strip()
    user = db.query(models.User).filter(models.User.email == email_clean).first()
    if not user: raise HTTPException(400, "User not found")
    if user.is_email_verified: return {"message": "Already verified", "status": "active", "role": user.role}
    if user.otp_expires_at and datetime.utcnow() > user.otp_expires_at: raise HTTPException(400, "OTP has expired")
    if str(user.otp_code).strip() != str(data.otp.strip()): raise HTTPException(400, "Invalid OTP")
    user.is_email_verified = True; user.otp_code = None
    db.commit()
    return {"message": "Verified", "status": "active", "role": user.role}

@auth_router.get("/me", response_model=schemas.UserOut)
def me(u: models.User = Depends(get_current_user), db: Session = Depends(get_db)): 
    if u.role == "doctor":
        d = db.query(models.Doctor).filter(models.Doctor.user_id == u.id).first()
        if d: u.specialization = d.specialization; 
    return u

@auth_router.put("/profile")
def update_user_profile(data: schemas.UserProfileUpdate, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if data.email != user.email:
        if db.query(models.User).filter(models.User.email == data.email).first(): raise HTTPException(400, "Email already in use")
        user.email = data.email
    user.full_name = data.full_name
    if data.phone_number: user.phone_number = data.phone_number
    if data.address: user.address = data.address
    if user.role == "doctor":
        d = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
        if d:
            if data.specialization: d.specialization = data.specialization
            if data.license_number: d.license_number = data.license_number
    if user.role == "organization":
        h = db.query(models.Hospital).filter(models.Hospital.owner_id == user.id).first()
        if h and data.phone_number: h.phone_number = data.phone_number
    db.commit()
    return {"message": "Profile updated successfully"}

@auth_router.get("/hospitals")
def get_verified_hospitals(db: Session = Depends(get_db)):
    hospitals = db.query(models.Hospital).filter(models.Hospital.is_verified == True).all()
    return [{"id": h.id, "name": h.name, "address": h.address} for h in hospitals]

@admin_router.get("/stats")
def get_admin_stats(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "admin": raise HTTPException(403)
    return {"doctors": db.query(models.Doctor).count(), "patients": db.query(models.Patient).count(), "organizations": db.query(models.Hospital).count(), "revenue": 0}

@admin_router.get("/doctors")
def get_all_doctors(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "admin": raise HTTPException(403)
    doctors = db.query(models.Doctor).all()
    return [{"id": d.id, "name": d.user.full_name if d.user else "Unknown", "email": d.user.email if d.user else "", "specialization": d.specialization, "license": d.license_number, "is_verified": d.is_verified, "hospital_name": d.hospital.name if d.hospital else "N/A"} for d in doctors]

@admin_router.get("/organizations")
def get_all_organizations(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "admin": raise HTTPException(403)
    orgs = db.query(models.Hospital).all()
    return [{"id": h.id, "name": h.name, "address": h.address, "owner_email": h.owner.email if h.owner else "", "is_verified": h.is_verified, "pending_address": h.pending_address, "pending_lat": h.pending_lat, "pending_lng": h.pending_lng} for h in orgs]

@admin_router.get("/patients")
def get_all_patients(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "admin": raise HTTPException(403)
    patients = db.query(models.Patient).all()
    results = []
    for p in patients:
        u = p.user
        results.append({"id": p.id, "name": u.full_name if u else "Unknown", "email": u.email if u else "Unknown", "age": p.age, "gender": p.gender, "created_at": u.created_at.strftime("%Y-%m-%d") if u else "N/A"})
    return results

@admin_router.get("/pending-requests")
def get_pending_requests(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "admin": raise HTTPException(403)
    pending_docs = db.query(models.Doctor).filter(models.Doctor.is_verified == False).all()
    pending_orgs = db.query(models.Hospital).filter(models.Hospital.is_verified == False).all()
    results = []
    for d in pending_docs:
        results.append({"id": d.id, "type": "doctor", "name": d.user.full_name, "email": d.user.email, "info": f"Spec: {d.specialization} | Lic: {d.license_number}", "date": d.user.created_at})
    for h in pending_orgs:
        results.append({"id": h.id, "type": "organization", "name": h.name, "email": h.owner.email, "info": f"Address: {h.address}", "date": h.owner.created_at})
    return results

@admin_router.get("/patients/{id}")
def get_admin_patient_details(id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "admin": raise HTTPException(403)
    p = db.query(models.Patient).filter(models.Patient.id == id).first()
    if not p: raise HTTPException(404, "Patient not found")
    recs = db.query(models.MedicalRecord).filter(models.MedicalRecord.patient_id == id).all()
    invs = db.query(models.Invoice).filter(models.Invoice.patient_id == id).all()
    return {"id": p.id, "full_name": p.user.full_name, "email": p.user.email, "phone": p.user.phone_number or "N/A", "age": p.age, "gender": p.gender, "address": p.user.address or "N/A", "blood_group": getattr(p, "blood_group", "N/A"), "history": [{"date": r.date, "diagnosis": r.diagnosis, "doctor": r.doctor.user.full_name} for r in recs], "invoices_count": len(invs), "last_visit": recs[-1].date if recs else None}

@admin_router.post("/approve-account/{id}")
def approve_account(id: int, type: str, db: Session = Depends(get_db)):
    if type == "organization":
        h = db.query(models.Hospital).filter(models.Hospital.id == id).first()
        if h: 
            if h.pending_address: h.address, h.lat, h.lng, h.pending_address = h.pending_address, h.pending_lat, h.pending_lng, None
            h.is_verified = True
    elif type == "doctor":
        d = db.query(models.Doctor).filter(models.Doctor.id == id).first()
        if d: d.is_verified = True
    db.commit(); return {"message": "Approved"}

@admin_router.delete("/delete/{type}/{id}")
def delete_entity(type: str, id: int, db: Session = Depends(get_db)):
    try:
        if type == "doctor":
            r = db.query(models.Doctor).filter(models.Doctor.id == id).first()
            if r: db.delete(r.user); db.delete(r)
        elif type == "organization":
            r = db.query(models.Hospital).filter(models.Hospital.id == id).first()
            if r: db.delete(r.owner); db.delete(r)
        db.commit(); return {"message": "Deleted"}
    except: db.rollback(); raise HTTPException(500, "Delete failed")

@org_router.get("/stats")
def get_org_stats(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "organization": raise HTTPException(403)
    h = db.query(models.Hospital).filter(models.Hospital.owner_id == user.id).first()
    if not h: return {}
    dids = [d.id for d in h.doctors]
    rev = db.query(func.sum(models.Invoice.amount)).join(models.Appointment).filter(models.Appointment.doctor_id.in_(dids), models.Invoice.status == "paid").scalar() or 0
    return {"total_doctors": len(h.doctors), "total_patients": 0, "total_revenue": rev, "utilization_rate": 80}

@org_router.get("/details")
def get_org_details(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "organization": raise HTTPException(403)
    h = db.query(models.Hospital).filter(models.Hospital.owner_id == user.id).first()
    return h

@org_router.get("/doctors")
def get_org_doctors(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    h = db.query(models.Hospital).filter(models.Hospital.owner_id == user.id).first()
    return [{"id": d.id, "full_name": d.user.full_name, "email": d.user.email, "specialization": d.specialization, "license": d.license_number, "is_verified": d.is_verified} for d in h.doctors]

@org_router.post("/location-request")
def request_location_change(data: schemas.LocationUpdate, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "organization": raise HTTPException(403)
    h = db.query(models.Hospital).filter(models.Hospital.owner_id == user.id).first()
    if not h: raise HTTPException(404, "Hospital profile not found")
    h.pending_address = data.address; h.pending_pincode = data.pincode; h.pending_lat = data.lat; h.pending_lng = data.lng
    db.commit()
    return {"message": "Location change requested. Waiting for Admin approval."}

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(auth_router); app.include_router(admin_router); app.include_router(org_router); 
@doctor_router.get("/invoices/{id}")
def get_invoice_detail(id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "doctor": raise HTTPException(403, "Not authorized")
    doc = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
    inv = db.query(models.Invoice).join(models.Appointment).filter(
        models.Invoice.id == id,
        models.Appointment.doctor_id == doc.id
    ).first()
    if not inv: raise HTTPException(404, "Invoice not found")
    appt = inv.appointment
    patient = appt.patient
    p_user = patient.user
    hospital = doc.hospital
    return {
        "id": inv.id,
        "date": inv.created_at.strftime("%Y-%m-%d"),
        "status": inv.status,
        "amount": inv.amount,
        "hospital": {
            "name": hospital.name if hospital else "Clinic",
            "address": hospital.address if hospital else "",
            "phone": ""
        },
        "doctor": {
            "name": user.full_name
        },
        "patient": {
            "id": patient.id,
            "name": p_user.full_name,
            "age": patient.age,
            "gender": patient.gender
        },
        "treatment": {
            "name": appt.treatment_type,
            "notes": appt.notes or ""
        }
    }
app.include_router(doctor_router); app.include_router(public_router)
app.include_router(agent_routes.router)
os.makedirs("media", exist_ok=True); app.mount("/media", StaticFiles(directory="media"), name="media")
