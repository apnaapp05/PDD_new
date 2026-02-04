
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
import models, schemas
from database import get_db
from core.security import get_current_user

router = APIRouter(prefix="/organization", tags=["Organization"])

@router.get("/stats")
def get_org_stats(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "organization": raise HTTPException(403)
    h = db.query(models.Hospital).filter(models.Hospital.owner_id == user.id).first()
    if not h: return {}
    dids = [d.id for d in h.doctors]
    rev = db.query(func.sum(models.Invoice.amount)).join(models.Appointment).filter(models.Appointment.doctor_id.in_(dids), models.Invoice.status == "paid").scalar() or 0
    return {"total_doctors": len(h.doctors), "total_patients": 0, "total_revenue": rev, "utilization_rate": 80}

@router.get("/details")
def get_org_details(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "organization": raise HTTPException(403)
    h = db.query(models.Hospital).filter(models.Hospital.owner_id == user.id).first()
    return h

@router.get("/doctors")
def get_org_doctors(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    h = db.query(models.Hospital).filter(models.Hospital.owner_id == user.id).first()
    return [{"id": d.id, "full_name": d.user.full_name, "email": d.user.email, "specialization": d.specialization, "license": d.license_number, "is_verified": d.is_verified} for d in h.doctors]

@router.post("/location-request")
def request_location_change(data: schemas.LocationUpdate, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "organization": raise HTTPException(403)
    h = db.query(models.Hospital).filter(models.Hospital.owner_id == user.id).first()
    if not h: raise HTTPException(404, "Hospital profile not found")
    h.pending_address = data.address; h.pending_pincode = data.pincode; h.pending_lat = data.lat; h.pending_lng = data.lng
    db.commit()
    return {"message": "Location change requested. Waiting for Admin approval."}
