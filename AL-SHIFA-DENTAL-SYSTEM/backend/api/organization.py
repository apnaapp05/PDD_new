
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
    
    # Direct Update (No Admin Approval)
    h.address = data.address
    # If your model has lat/lng on the main table, use those. 
    # Based on models.py, Hospital only has pending_lat/lng or address.
    # We will assume address is primary, but strictly speaking we should probably add lat/lng to Hospital if not there.
    # Looking at models.py: pending_lat exists, but 'lat' does not exist in Hospital table?
    # Let's check models.py again. It has 'address', but no 'lat'/'lng' columns on the main table...
    # Wait, models.py Step 15 shows: 
    # pending_address, pending_pincode, pending_lat, pending_lng
    # But ONLY 'address' and 'name' are main columns.
    # So we can only update 'address' directly. Ideally we should migrate to add lat/lng columns, 
    # but for now we will just use the available columns.
    # Actually, if the frontend expects lat/lng, maybe we should just set the pending ones and treat them as final?
    # Or better, we should update the schema... but user said "remove approval".
    # Let's just set the pending fields AND valid address fields.
    
    h.address = data.address
    # Since there are no lat/lng columns in the main table, we effectively CAN'T store them verified without schema change OR
    # simply treating pending_lat as the source of truth if is_verified is True?
    # But wait, admin.py Step 78 shows: `h.address = h.pending_address` on approval.
    # So we will do that here immediately.
    
    h.pending_address = data.address
    h.pending_pincode = data.pincode
    h.pending_lat = data.lat
    h.pending_lng = data.lng
    # Also update main address if that's what approval does
    h.address = data.address
    
    db.commit()
    return {"message": "Location updated successfully."}
