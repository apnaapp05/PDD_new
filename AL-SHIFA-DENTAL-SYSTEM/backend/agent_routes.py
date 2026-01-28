# backend/agent_routes.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from datetime import datetime, date, timedelta
from typing import List, Optional
import re
import logging

from services.llm_service import llm_client
from dependencies import get_current_user, get_db
import models

router = APIRouter(prefix="/agent", tags=["AI Agents"])
logger = logging.getLogger(__name__)

class AgentRequest(BaseModel):
    user_query: str
    role: str
    history: List[dict] = [] 

def execute_action(db: Session, doctor_id: int, agent_role: str, action_cmd: str, current_user_id: int = None) -> str:
    try:
        print(f"🔹 ACTION RECEIVED: {action_cmd}")
        parts = [p.strip() for p in action_cmd.strip().split("|")]
        command = parts[0].replace("ACTION:", "").strip().upper()
        
        # STRICT CHECK: Only BOOK_SELF is allowed for patients
        if agent_role == "patient_booking" and command == "BOOK_SELF":
            if len(parts) < 5: return "❌ Error: Missing info."
            doc_name, date_str, time_str, reason = parts[1], parts[2], parts[3], parts[4]
            
            clean_name = doc_name.replace("Dr.", "").replace("Doctor", "").strip()
            doc = db.query(models.Doctor).join(models.User).filter(models.User.full_name.ilike(f"%{clean_name}%")).first()
            if not doc: doc = db.query(models.Doctor).join(models.User).filter(models.User.full_name.ilike(f"%{clean_name.split()[-1]}%")).first()
            if not doc: return f"❌ Doctor not found."

            pat = db.query(models.Patient).filter(models.Patient.user_id == current_user_id).first()
            
            try: 
                time_str = time_str.replace(".", "").upper()
                start_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %I:%M %p")
            except: 
                try: start_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                except: return f"❌ Invalid time."
            
            conflict = db.query(models.Appointment).filter(models.Appointment.doctor_id == doc.id, models.Appointment.start_time == start_dt, models.Appointment.status != "cancelled").first()
            if conflict: return f"❌ Slot taken. [STATE: SELECT_TIME]"
            
            new_appt = models.Appointment(doctor_id=doc.id, patient_id=pat.id, start_time=start_dt, end_time=start_dt+timedelta(minutes=30), status="confirmed", treatment_type=reason, notes="AI Booking")
            db.add(new_appt)
            
            cost = 0
            t = db.query(models.Treatment).filter(models.Treatment.hospital_id == doc.hospital_id, models.Treatment.name == reason).first()
            if t: cost = t.cost
            db.add(models.Invoice(appointment=new_appt, patient_id=pat.id, amount=cost, status="pending"))
            
            db.commit()
            return f"✅ Confirmed! Dr. {doc.user.full_name} on {date_str} at {time_str}. [STATE: DONE]"

        # If we get here, it means the AI sent a command that isn't BOOK_SELF.
        # Instead of crashing, we return a fallback state tag.
        print(f"⚠️ IGNORED UNKNOWN COMMAND: {command}")
        return "Please continue. [STATE: SELECT_TIME]" 

    except Exception as e: return f"❌ System Error: {str(e)}"

def get_patient_booking_context(db: Session) -> str:
    hospitals = db.query(models.Hospital).filter(models.Hospital.is_verified == True).all()
    lines = ["DATABASE:"]
    for h in hospitals:
        lines.append(f"HOSPITAL: {h.name}")
        for d in h.doctors:
            lines.append(f" - DOCTOR: {d.user.full_name}")
    return "\n".join(lines)

# Stubs
def get_appointment_context(db, did): return "Data"
def get_revenue_context(db, did): return "Data"
def get_inventory_context(db, hid): return "Data"
def get_casetracking_context(db, did, q): return "Data"

@router.post("/router")
async def route_agent(
    request: AgentRequest, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
):
    try:
        agent = request.role.lower().replace(" ", "")
        today = datetime.now().strftime("%Y-%m-%d")
        
        if agent == "patient_booking":
            context_data = get_patient_booking_context(db)
            
            instr = (
                f"You are a Logic Engine. TODAY: {today}\n"
                "Your Job: Output the NEXT STATE tag based on what is missing.\n"
                "The ONLY valid 'ACTION' is 'ACTION: BOOK_SELF'. Do NOT use ACTION for anything else.\n\n"
                "LOGIC FLOW:\n"
                "1. Hospital missing? -> 'Select a hospital.' [STATE: SELECT_HOSPITAL]\n"
                "2. Doctor missing? -> 'Select a doctor.' [STATE: SELECT_DOCTOR]\n"
                "3. Date missing? -> 'Select a date.' [STATE: SELECT_DATE]\n"
                "4. Time missing? -> 'Select a time.' [STATE: SELECT_TIME]\n"
                "5. Reason missing? -> 'Select a reason.' [STATE: SELECT_REASON]\n"
                "6. ALL INFO PRESENT? -> ACTION: BOOK_SELF | Name | YYYY-MM-DD | HH:MM AM/PM | Reason\n\n"
                "NOTE: If user just gave a Date, you MUST assume Time is missing (Step 4) and output [STATE: SELECT_TIME]."
            )
            
            full_prompt = f"<|system|>\n{instr}\n\nDATA:\n{context_data}<|end|>\n"
            for msg in request.history[-6:]:
                role = "user" if msg['role'] == "user" else "assistant"
                full_prompt += f"<|{role}|>\n{msg['text']}<|end|>\n"
            full_prompt += f"<|user|>\n{request.user_query}<|end|>\n<|assistant|>"
            
            res = llm_client.generate_response(full_prompt)
            
            # SAFETY FILTER: Only execute if it's a BOOK_SELF command
            if "ACTION:" in res:
                if "BOOK_SELF" in res:
                    match = re.search(r"ACTION:.*", res)
                    if match: return {"response": execute_action(db, 0, agent, match.group(0), user.id), "agent": agent}
                else:
                    # AI hallucinated a weird action. Ignore it and just return the text part.
                    # Or force a default state.
                    return {"response": "Please continue. [STATE: SELECT_TIME]", "agent": agent}
            
            return {"response": res, "agent": agent}

        return {"response": "Active.", "agent": agent}
    except Exception as e: return {"response": "System Error."}
