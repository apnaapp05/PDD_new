
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import models
from database import get_db
from core.security import get_current_user

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/stats")
def get_admin_stats(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "admin": raise HTTPException(403)
    return {"doctors": db.query(models.Doctor).count(), "patients": db.query(models.Patient).count(), "organizations": db.query(models.Hospital).count(), "revenue": 0}

@router.get("/doctors")
def get_all_doctors(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "admin": raise HTTPException(403)
    doctors = db.query(models.Doctor).all()
    return [{"id": d.id, "name": d.user.full_name if d.user else "Unknown", "email": d.user.email if d.user else "", "specialization": d.specialization, "license": d.license_number, "is_verified": d.is_verified, "hospital_name": d.hospital.name if d.hospital else "N/A"} for d in doctors]

@router.get("/organizations")
def get_all_organizations(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "admin": raise HTTPException(403)
    orgs = db.query(models.Hospital).all()
    return [{"id": h.id, "name": h.name, "address": h.address, "owner_email": h.owner.email if h.owner else "", "is_verified": h.is_verified, "pending_address": h.pending_address, "pending_lat": h.pending_lat, "pending_lng": h.pending_lng} for h in orgs]

@router.get("/patients")
def get_all_patients(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "admin": raise HTTPException(403)
    patients = db.query(models.Patient).all()
    results = []
    for p in patients:
        u = p.user
        results.append({"id": p.id, "name": u.full_name if u else "Unknown", "email": u.email if u else "Unknown", "age": p.age, "gender": p.gender, "created_at": u.created_at.strftime("%Y-%m-%d") if u else "N/A"})
    return results

@router.get("/pending-requests")
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

@router.get("/patients/{id}")
def get_admin_patient_details(id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "admin": raise HTTPException(403)
    p = db.query(models.Patient).filter(models.Patient.id == id).first()
    if not p: raise HTTPException(404, "Patient not found")
    recs = db.query(models.MedicalRecord).filter(models.MedicalRecord.patient_id == id).all()
    invs = db.query(models.Invoice).filter(models.Invoice.patient_id == id).all()
    return {"id": p.id, "full_name": p.user.full_name, "email": p.user.email, "phone": p.user.phone_number or "N/A", "age": p.age, "gender": p.gender, "address": p.user.address or "N/A", "blood_group": getattr(p, "blood_group", "N/A"), "history": [{"date": r.date, "diagnosis": r.diagnosis, "doctor": r.doctor.user.full_name} for r in recs], "invoices_count": len(invs), "last_visit": recs[-1].date if recs else None}

@router.post("/approve-account/{id}")
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

@router.delete("/delete/{type}/{id}")
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
