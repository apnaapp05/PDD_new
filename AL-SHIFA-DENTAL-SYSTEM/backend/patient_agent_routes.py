from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from auth_dependency import get_current_user
from models import User, Patient
from agent.patient_brain import PatientBrain
from pydantic import BaseModel

router = APIRouter(prefix="/patient/agent", tags=["Patient AI"])

class ChatRequest(BaseModel):
    query: str

@router.post("/chat")
def patient_chat(request: ChatRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "patient":
        raise HTTPException(status_code=403, detail="Access denied")
    
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found")

    brain = PatientBrain(db, patient.id)
    return brain.process(request.query)
