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

# ==============================================================================
# 1. UNIVERSAL ACTION EXECUTOR
# ==============================================================================
def execute_action(db: Session, doctor_id: int, agent_role: str, action_cmd: str, current_user_id: int = None) -> str:
    try:
        print(f"🔹 EXECUTING: {action_cmd}")
        parts = [p.strip() for p in action_cmd.strip().split("|")]
        command = parts[0].replace("ACTION:", "").strip().upper()
        
        # --- DOCTOR: CANCEL ---
        if agent_role == "appointment" and command == "CANCEL":
            # ACTION: CANCEL | ID
            if len(parts) < 2: return "❌ Error: ID missing."
            try: aid = int(parts[1])
            except: return "❌ Error: ID must be a number."
            
            appt = db.query(models.Appointment).filter(models.Appointment.id == aid, models.Appointment.doctor_id == doctor_id).first()
            if not appt: return f"❌ Appointment #{aid} not found."
            
            # Perform Cancellation
            appt.status = "cancelled"
            inv = db.query(models.Invoice).filter(models.Invoice.appointment_id == aid, models.Invoice.status == "pending").first()
            if inv: inv.status = "cancelled"
            
            db.commit()
            return f"✅ SUCCESS: Appointment #{aid} at {appt.start_time.strftime('%I:%M %p')} has been deleted."

        # --- DOCTOR: BOOK ---
        elif agent_role == "appointment" and command == "BOOK":
            if len(parts) < 5: return "❌ Error: Missing details."
            d, t, p_name, r = parts[1], parts[2], parts[3], parts[4]
            try: 
                t = t.replace(".", "").upper()
                start_dt = datetime.strptime(f"{d} {t}", "%Y-%m-%d %I:%M %p")
            except: return "❌ Invalid Time."
            
            p = db.query(models.Patient).join(models.User).filter(models.User.full_name.ilike(f"%{p_name}%")).first()
            if not p: return f"❌ Patient '{p_name}' not found."

            db.add(models.Appointment(doctor_id=doctor_id, patient_id=p.id, start_time=start_dt, end_time=start_dt+timedelta(minutes=30), status="confirmed", treatment_type=r))
            db.commit()
            return f"✅ Booked {p_name}."

        # --- PATIENT: BOOK SELF ---
        elif agent_role == "patient_booking" and command == "BOOK_SELF":
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

        # --- OTHER DOCTOR TOOLS ---
        elif agent_role == "revenue" and command == "UPDATE_INVOICE":
            inv = db.query(models.Invoice).filter(models.Invoice.id == parts[1]).first()
            if inv: inv.status = parts[2].lower(); db.commit(); return f"✅ Invoice #{parts[1]} updated."
            return "❌ Not found."

        elif agent_role == "inventory" and command == "UPDATE_STOCK":
            item = db.query(models.InventoryItem).filter(models.InventoryItem.name.ilike(f"%{parts[1]}%")).first()
            if item: item.quantity = int(parts[2]); db.commit(); return f"✅ {item.name} stock updated."
            return "❌ Not found."

        elif agent_role == "casetracking" and command == "ADD_RECORD":
            p = db.query(models.Patient).join(models.User).filter(models.User.full_name.ilike(f"%{parts[1]}%")).first()
            if p: 
                db.add(models.MedicalRecord(patient_id=p.id, doctor_id=doctor_id, diagnosis=parts[2], prescription=parts[3], date=datetime.utcnow()))
                db.commit()
                return "✅ Record added."
            return "❌ Patient not found."

        return "❌ Error: Unknown Command."
    except Exception as e: return f"❌ System Error: {str(e)}"

# ==============================================================================
# 2. CONTEXT LOADERS
# ==============================================================================
def get_appointment_context(db: Session, doctor_id: int) -> str:
    now = datetime.now()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=7)
    appts = db.query(models.Appointment).filter(models.Appointment.doctor_id == doctor_id, models.Appointment.start_time >= start, models.Appointment.start_time <= end, models.Appointment.status != "cancelled").order_by(models.Appointment.start_time).all()
    
    if not appts: return "SCHEDULE DATA: [EMPTY] No upcoming appointments."
    lines = ["SCHEDULE DATA (Use these IDs to Cancel):"]
    for a in appts:
        p_name = a.patient.user.full_name if (a.patient and a.patient.user) else "Unknown"
        date_str = a.start_time.strftime('%Y-%m-%d')
        time_str = a.start_time.strftime('%I:%M %p')
        lines.append(f"- ID: {a.id} | {date_str} {time_str} | {p_name}")
    return "\n".join(lines)

def get_revenue_context(db, did): return "FINANCIAL DATA..."
def get_inventory_context(db, hid): return "INVENTORY DATA..."
def get_casetracking_context(db, did, q): return "PATIENT HISTORY..."
def get_patient_booking_context(db): return "HOSPITAL DATA..."

# ==============================================================================
# 3. ROUTER
# ==============================================================================
@router.post("/router")
async def route_agent(
    request: AgentRequest, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
):
    try:
        agent = request.role.lower().replace(" ", "")
        today = datetime.now().strftime("%Y-%m-%d")

        # --- PATH 1: PATIENT (Wizard) ---
        if agent == "patient_booking":
            context_data = get_patient_booking_context(db)
            instr = (
                f"You are a Logic Gate. TODAY: {today}\n"
                "Determine state from chat history.\n"
                "LOGIC:\n"
                "1. Hospital? -> [STATE: SELECT_HOSPITAL]\n"
                "2. Doctor? -> [STATE: SELECT_DOCTOR]\n"
                "3. Date? -> [STATE: SELECT_DATE]\n"
                "4. Time? -> [STATE: SELECT_TIME]\n"
                "5. Reason? -> [STATE: SELECT_REASON]\n"
                "6. Done? -> ACTION: BOOK_SELF ..."
            )
            full_prompt = f"<|system|>\n{instr}\n\nDATA:\n{context_data}<|end|>\n"
            for msg in request.history[-6:]:
                role = "user" if msg['role'] == "user" else "assistant"
                full_prompt += f"<|{role}|>\n{msg['text']}<|end|>\n"
            full_prompt += f"<|user|>\n{request.user_query}<|end|>\n<|assistant|>"
            
            res = llm_client.generate_response(full_prompt)
            if "ACTION:" in res:
                 match = re.search(r"ACTION:.*", res)
                 if match: return {"response": execute_action(db, 0, agent, match.group(0), user.id), "agent": agent}
            return {"response": res, "agent": agent}

        # --- PATH 2: DOCTOR (Strict Command Mode) ---
        doctor = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
        if not doctor: return {"response": "Error: Doctor profile not found."}

        context_data = ""
        instr = ""
        
        if agent == "appointment":
            context_data = get_appointment_context(db, doctor.id)
            instr = (
                f"You are a CLI Command Generator. TODAY: {today}\n"
                "DATA:\n{context_data}\n\n"
                "TASK: Convert user request to a Database Command.\n"
                "RULES:\n"
                "1. To CANCEL: Look at DATA. Find the ID for the requested time. Output: ACTION: CANCEL | [ID]\n"
                "2. EXAMPLE: User says 'Cancel 11:30'. DATA shows 'ID: 5 | ... 11:30 AM'. Output: ACTION: CANCEL | 5\n"
                "3. DO NOT CHAT. DO NOT SAY 'I have cancelled'. JUST OUTPUT THE COMMAND.\n"
                "4. If ID is unclear, ask 'Please provide the ID'."
            )
        elif agent == "revenue":
            context_data = get_revenue_context(db, doctor.id)
            instr = "You are a Finance Manager."
        elif agent == "inventory":
            context_data = get_inventory_context(db, doctor.hospital_id)
            instr = "You are an Inventory Manager."
        elif agent == "casetracking":
            context_data = get_casetracking_context(db, doctor.id, request.user_query)
            instr = "You are a Clinical Assistant."

        full_prompt = f"<|system|>\n{instr}\n<|end|>\n"
        for msg in request.history[-5:]:
            role = "user" if msg['role'] == "user" else "assistant"
            full_prompt += f"<|{role}|>\n{msg['text']}<|end|>\n"
        full_prompt += f"<|user|>\n{request.user_query}<|end|>\n<|assistant|>"

        res = llm_client.generate_response(full_prompt)
        
        # EXECUTE IF ACTION FOUND
        if "ACTION:" in res:
            match = re.search(r"ACTION:.*", res)
            if match: return {"response": execute_action(db, doctor.id, agent, match.group(0), user.id), "agent": agent}

        return {"response": res, "agent": agent}

    except Exception as e: return {"response": f"System Error: {str(e)}"}
