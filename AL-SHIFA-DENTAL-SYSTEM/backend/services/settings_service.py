from sqlalchemy.orm import Session
from models import User, Doctor

class SettingsService:
    def __init__(self, db: Session, doctor_id: int):
        self.db = db
        self.doctor_id = doctor_id

    def update_working_hours(self, start_time: str, end_time: str):
        # Robust lookup by ID or UserID
        doctor = self.db.query(Doctor).filter((Doctor.id == self.doctor_id) | (Doctor.user_id == self.doctor_id)).first()
        if not doctor:
            raise ValueError("Doctor profile not found.")
        
        doctor.start_time = start_time
        doctor.end_time = end_time
        self.db.commit()
        self.db.refresh(doctor)
        return doctor

    def change_password(self, current_password: str, new_password: str):
        # LAZY IMPORT: Moved inside to prevent 'ModuleNotFoundError' at startup
        try:
            from core.security import get_password_hash, verify_password
        except ImportError:
            # Fallback for different folder structures
            from backend.core.security import get_password_hash, verify_password

        user = self.db.query(User).filter(User.id == self.doctor_id).first()
        if not user:
             # Try finding via Doctor link if User ID mismatch
             user = self.db.query(User).join(Doctor).filter(Doctor.id == self.doctor_id).first()
        
        if not user:
            raise ValueError("User not found")
            
        if not verify_password(current_password, user.hashed_password):
            raise ValueError("Incorrect current password")
            
        user.hashed_password = get_password_hash(new_password)
        self.db.commit()
        return True
