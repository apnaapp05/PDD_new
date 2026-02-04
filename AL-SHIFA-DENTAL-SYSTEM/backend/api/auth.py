
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging

import models, schemas
from database import get_db
from core.security import verify_password, create_access_token, get_current_user, get_password_hash
from core.utils import generate_otp, get_otp_email_template
from core.email import email_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/login")
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

@router.post("/register")
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

@router.post("/verify-otp")
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

@router.get("/me", response_model=schemas.UserOut)
def me(u: models.User = Depends(get_current_user), db: Session = Depends(get_db)): 
    if u.role == "doctor":
        d = db.query(models.Doctor).filter(models.Doctor.user_id == u.id).first()
        if d: u.specialization = d.specialization; 
    return u

@router.put("/profile")
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

@router.get("/hospitals")
def get_verified_hospitals(db: Session = Depends(get_db)):
    hospitals = db.query(models.Hospital).filter(models.Hospital.is_verified == True).all()
    return [{"id": h.id, "name": h.name, "address": h.address} for h in hospitals]
