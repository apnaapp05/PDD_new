
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import json
import models, schemas
from database import get_db
from core.security import get_current_user
from core.utils import generate_otp

router = APIRouter(tags=["Public"]) 

@router.get("/")
def health_check():
    return {"status": "running", "system": "Al-Shifa Dental API"}

@router.get("/doctors")
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

@router.get("/doctors/{doctor_id}/treatments")
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

@router.get("/doctors/{doctor_id}/settings")
def get_public_doctor_settings(doctor_id: int, db: Session = Depends(get_db)):
    doc = db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()
    if not doc: raise HTTPException(404, "Doctor not found")
    default_settings = {"work_start_time": "09:00", "work_end_time": "17:00", "slot_duration": 30}
    if not doc.scheduling_config: return default_settings
    try: return json.loads(doc.scheduling_config)
    except: return default_settings

@router.get("/doctors/{doctor_id}/booked-slots")
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

@router.post("/appointments")
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

    db.commit(); db.refresh(new_appt)
    return {"message": "Booked", "id": new_appt.id}

@router.get("/patient/appointments")
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

@router.put("/patient/appointments/{appt_id}/cancel")
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

@router.get("/patient/invoices")
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

@router.get("/patient/invoices/{id}")
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

@router.get("/patient/records")
def get_my_records(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = db.query(models.Patient).filter(models.Patient.user_id == user.id).first()
    if not p: return []
    recs = db.query(models.MedicalRecord).filter(models.MedicalRecord.patient_id == p.id).order_by(models.MedicalRecord.date.desc()).all()
    return [{"id": r.id, "diagnosis": r.diagnosis, "prescription": r.prescription, "date": r.date.strftime("%Y-%m-%d"), "doctor_name": r.doctor.user.full_name} for r in recs]

@router.get("/patient/profile")
def get_patient_profile(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "patient": raise HTTPException(403)
    p = db.query(models.Patient).filter(models.Patient.user_id == user.id).first()
    if not p: raise HTTPException(404, "Patient profile not found")
    return {
        "id": p.id, "full_name": user.full_name, "email": user.email,
        "age": p.age, "gender": p.gender, "address": user.address or "", 
        "blood_group": getattr(p, "blood_group", "")
    }

@router.put("/patient/profile")
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
