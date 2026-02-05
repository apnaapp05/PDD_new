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

    # --- SESSION PERSISTENCE ---
    global CHAT_SESSIONS
    if 'CHAT_SESSIONS' not in globals():
        CHAT_SESSIONS = {}

    if patient.id not in CHAT_SESSIONS:
        CHAT_SESSIONS[patient.id] = PatientBrain(db, patient.id)
    
    brain = CHAT_SESSIONS[patient.id]
    
    # CRITICAL: Update DB session for this request (old session is closed)
    brain.db = db
    brain.tool_engine.db = db
    brain.tool_engine.appt_service.db = db
    # ---------------------------
    try:
        print(f"DEBUG: Processing query: {request.query}")
        response_text = brain.process(request.query)
        
        # CRITICAL: Commit any database changes made by tools
        try:
            db.commit()
            print("DEBUG: Database changes committed successfully")
        except Exception as commit_err:
            print(f"DEBUG: Commit failed: {commit_err}")
            db.rollback()
        
        print(f"DEBUG: Brain returned: {response_text!r}")
        
        # Return consistent format
        if isinstance(response_text, dict):
            return response_text
        else:
            return {"response": response_text, "text": response_text}
            
    except Exception as e:
        print(f"DEBUG: Error in route: {e}")
        db.rollback()
        return {"response": f"❌ Error: {str(e)}", "text": f"❌ Error: {str(e)}"}

