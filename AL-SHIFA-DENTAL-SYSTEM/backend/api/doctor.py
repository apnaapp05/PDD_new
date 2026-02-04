
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
import csv
import json
import shutil
import os

import models, schemas
from database import get_db
from core.security import get_current_user
from services.analytics_service import AnalyticsService

router = APIRouter(prefix="/doctor", tags=["Doctor"])

@router.put("/inventory/{item_id}")
def update_inventory_item(item_id: int, data: schemas.InventoryUpdate, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "doctor": raise HTTPException(403)
    doctor = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
    item = db.query(models.InventoryItem).filter(models.InventoryItem.id == item_id, models.InventoryItem.hospital_id == doctor.hospital_id).first()
    if not item: raise HTTPException(404)
    item.quantity = data.quantity; item.last_updated = datetime.utcnow()
    db.commit()
    return {"message": "Updated", "new_quantity": item.quantity}

@router.get("/dashboard")
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

@router.post("/appointments/{id}/start")
def start_appointment(id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
    appt = db.query(models.Appointment).filter(models.Appointment.id == id, models.Appointment.doctor_id == doc.id).first()
    if not appt: raise HTTPException(404)
    appt.status = "in_progress"; db.commit()
    return {"message": "Started", "status": "in_progress"}

@router.post("/appointments/{id}/complete")
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

@router.post("/treatments/upload")
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

@router.post("/inventory/upload")
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

@router.get("/treatments")
def get_doc_treatments(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
    treatments = db.query(models.Treatment).filter(models.Treatment.doctor_id == doc.id).all()
    results = []
    for t in treatments:
        recipe = [{"item_name": l.item.name, "qty_required": l.quantity_required, "unit": l.item.unit} for l in t.required_items]
        results.append({"id": t.id, "name": t.name, "cost": t.cost, "description": t.description, "recipe": recipe})
    return results

@router.post("/treatments")
def create_treatment(data: schemas.TreatmentCreate, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
    
    if db.query(models.Treatment).filter(models.Treatment.doctor_id == doc.id, models.Treatment.name == data.name).first():
        raise HTTPException(400, "Treatment already exists")

    db.add(models.Treatment(hospital_id=doc.hospital_id, doctor_id=doc.id, name=data.name, cost=data.cost, description=data.description))
    db.commit()
    return {"message": "Created"}

@router.post("/treatments/{tid}/link-inventory")
def link_inv(tid: int, data: schemas.TreatmentLinkCreate, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    link = db.query(models.TreatmentInventoryLink).filter(models.TreatmentInventoryLink.treatment_id == tid, models.TreatmentInventoryLink.item_id == data.item_id).first()
    if link: link.quantity_required = data.quantity
    else: db.add(models.TreatmentInventoryLink(treatment_id=tid, item_id=data.item_id, quantity_required=data.quantity))
    db.commit(); return {"message": "Linked"}

@router.get("/inventory")
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

@router.post("/inventory")
def add_inv(item: schemas.InventoryItemCreate, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
    db.add(models.InventoryItem(hospital_id=doc.hospital_id, name=item.name, quantity=item.quantity, unit=item.unit, min_threshold=item.min_threshold))
    db.commit(); return {"message": "Added"}

@router.get("/schedule")
def get_sched(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
    return db.query(models.Appointment).filter(
        models.Appointment.doctor_id == doc.id,
        models.Appointment.status != "cancelled" 
    ).all()

@router.get("/appointments")
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

@router.post("/schedule/block")
def block_slot(data: schemas.BlockSlotCreate, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "doctor": raise HTTPException(403)
    doc = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
    
    start_dt = datetime.strptime(f"{data.date} {data.time or '00:00'}", "%Y-%m-%d %H:%M")
    end_dt = start_dt + timedelta(minutes=30) 
    if data.is_whole_day: end_dt = start_dt + timedelta(days=1)
        
    db.add(models.Appointment(doctor_id=doc.id, patient_id=None, start_time=start_dt, end_time=end_dt, status="blocked", notes=data.reason))
    db.commit(); return {"message": "Blocked"}

@router.get("/schedule/settings")
def get_schedule_settings(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "doctor": raise HTTPException(403)
    doc = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
    if not doc.scheduling_config: return {"work_start_time": "09:00", "work_end_time": "17:00", "slot_duration": 30}
    try: return json.loads(doc.scheduling_config)
    except: return {"work_start_time": "09:00", "work_end_time": "17:00", "slot_duration": 30}

@router.put("/schedule/settings")
def update_schedule_settings(settings: dict, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "doctor": raise HTTPException(403)
    doc = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
    doc.scheduling_config = json.dumps(settings)
    db.commit()
    return {"message": "Settings updated"}

@router.get("/finance")
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

@router.get("/patients")
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

@router.post("/patients")
def create_patient_by_doctor(data: schemas.PatientCreateByDoctor, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "doctor": raise HTTPException(403)
    if db.query(models.User).filter(models.User.email == data.email).first(): raise HTTPException(400, "Email already registered")
    
    from core.security import get_password_hash # Lazy import to avoid cycle if any
    pwd = get_password_hash("123456") 
    new_user = models.User(email=data.email, password_hash=pwd, full_name=data.full_name, role="patient", is_email_verified=True)
    db.add(new_user); db.flush()
    new_patient = models.Patient(user_id=new_user.id, age=data.age, gender=data.gender)
    db.add(new_patient); db.commit()
    
    doc = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
    db.add(models.MedicalRecord(patient_id=new_patient.id, doctor_id=doc.id, diagnosis="New Patient Registration", prescription="", notes="Registered by Doctor"))
    db.commit()
    return {"message": "Patient created", "id": new_patient.id}

@router.get("/patients/{id}")
def get_pat_det(id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = db.query(models.Patient).filter(models.Patient.id == id).first()
    if not p: raise HTTPException(404, "Patient not found")
    recs = db.query(models.MedicalRecord).filter(models.MedicalRecord.patient_id == id).all()
    files = db.query(models.PatientFile).filter(models.PatientFile.patient_id == id).all()
    return {"id": p.id, "full_name": p.user.full_name, "age": p.age, "gender": p.gender, 
            "history": [{"date": r.date.strftime("%Y-%m-%d"), "diagnosis": r.diagnosis, "prescription": r.prescription, "doctor_name": r.doctor.user.full_name} for r in recs],
            "files": [{"id": f.id, "filename": f.filename, "path": f.filepath, "date": f.uploaded_at.strftime("%Y-%m-%d")} for f in files]}

@router.post("/patients/{patient_id}/files")
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

@router.post("/patients/{id}/records")
def add_rec(id: int, data: schemas.RecordCreate, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
    db.add(models.MedicalRecord(patient_id=id, doctor_id=doc.id, diagnosis=data.diagnosis, prescription=data.prescription, notes=data.notes, date=datetime.utcnow()))
    db.commit(); return {"message": "Saved"}

@router.get("/invoices/{id}")
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
