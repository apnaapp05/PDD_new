# backend/agent_routes.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
import logging
import re

from services.llm_service import llm_client
from dependencies import get_current_user, get_db
import models

router = APIRouter(prefix="/agent", tags=["AI Agents"])
logger = logging.getLogger(__name__)

class AgentRequest(BaseModel):
    user_query: str
    role: str
    # FIX: Use built-in list[dict] to avoid NameError
    history: list[dict] = [] 

# ==============================================================================
# 1. ACTION EXECUTOR (DATABASE ACTIONS)
# ==============================================================================
def execute_action(db: Session, doctor_id: int, agent_role: str, action_cmd: str, current_user_id: int = None) -> str:
    try:
        print(f"🔹 EXECUTING: {action_cmd}")
        parts = [p.strip() for p in action_cmd.strip().split("|")]
        command = parts[0].replace("ACTION:", "").strip().upper()
        
        # --- DOCTOR: APPOINTMENT ---
        if agent_role == "appointment":
            if command == "CANCEL":
                # ACTION: CANCEL | ID
                if len(parts) < 2: return "❌ Error: ID missing."
                try: aid = int(parts[1])
                except: return "❌ Error: ID must be a number."
                
                appt = db.query(models.Appointment).filter(models.Appointment.id == aid, models.Appointment.doctor_id == doctor_id).first()
                if not appt: return f"❌ Appointment #{aid} not found."
                
                appt.status = "cancelled"
                inv = db.query(models.Invoice).filter(models.Invoice.appointment_id == aid, models.Invoice.status == "pending").first()
                if inv: inv.status = "cancelled"
                
                db.commit()
                return f"✅ SUCCESS: Appointment #{aid} CANCELLED."

            elif command == "BOOK":
                # ACTION: BOOK | YYYY-MM-DD | HH:MM | PatientName | Reason
                if len(parts) < 5: return "❌ Error: Missing details."
                d, t, p_name, r = parts[1], parts[2], parts[3], parts[4]
                try: 
                    t = t.replace(".", "").upper()
                    s = datetime.strptime(f"{d} {t}", "%Y-%m-%d %I:%M %p")
                except: 
                    try: s = datetime.strptime(f"{d} {t}", "%Y-%m-%d %H:%M")
                    except: return "❌ Error: Invalid Time Format."
                
                p = db.query(models.Patient).join(models.User).filter(models.User.full_name.ilike(f"%{p_name}%")).first()
                if not p: return f"❌ Error: Patient '{p_name}' not found."

                db.add(models.Appointment(doctor_id=doctor_id, patient_id=p.id, start_time=s, end_time=s+timedelta(minutes=30), status="confirmed", treatment_type=r))
                db.commit()
                return f"✅ SUCCESS: Booked {p_name}."

        # --- DOCTOR: REVENUE ---
        elif agent_role == "revenue" and command == "UPDATE_INVOICE":
            # ACTION: UPDATE_INVOICE | ID | STATUS
            if len(parts) < 3: return "❌ Error: Missing ID/Status."
            inv = db.query(models.Invoice).filter(models.Invoice.id == parts[1]).first()
            if inv: 
                inv.status = parts[2].lower()
                db.commit()
                return f"✅ Invoice #{parts[1]} updated to {parts[2]}."
            return "❌ Invoice not found."

        # --- DOCTOR: INVENTORY ---
        elif agent_role == "inventory" and command == "UPDATE_STOCK":
            # ACTION: UPDATE_STOCK | ItemName | Qty
            if len(parts) < 3: return "❌ Error: Missing Item/Qty."
            item = db.query(models.InventoryItem).filter(models.InventoryItem.name.ilike(f"%{parts[1]}%")).first()
            if item: 
                item.quantity = int(parts[2])
                db.commit()
                return f"✅ {item.name} stock updated to {parts[2]}."
            return "❌ Item not found."

        # --- DOCTOR: RECORDS ---
        elif agent_role == "casetracking" and command == "ADD_RECORD":
            # ACTION: ADD_RECORD | PatientName | Diagnosis | Rx
            if len(parts) < 4: return "❌ Error: Missing details."
            p = db.query(models.Patient).join(models.User).filter(models.User.full_name.ilike(f"%{parts[1]}%")).first()
            if p: 
                rec = models.MedicalRecord(patient_id=p.id, doctor_id=doctor_id, diagnosis=parts[2], prescription=parts[3], date=datetime.utcnow())
                db.add(rec)
                db.commit()
                return "✅ Record Saved."
            return "❌ Patient not found."

        # --- PATIENT: WIZARD BOOKING ---
        elif agent_role == "patient_booking" and command == "BOOK_SELF":
            # Simple pass-through for wizard
            return f"✅ Booking Processed."

        return "❌ Error: Unknown Command."
    except Exception as e: return f"❌ System Error: {str(e)}"

# ==============================================================================
# 2. CONTEXT LOADERS (REAL DATA)
# ==============================================================================
def get_appointment_context(db: Session, doctor_id: int) -> str:
    now = datetime.now()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=7)
    appts = db.query(models.Appointment).filter(models.Appointment.doctor_id == doctor_id, models.Appointment.start_time >= start, models.Appointment.start_time <= end, models.Appointment.status != "cancelled").order_by(models.Appointment.start_time).all()
    
    if not appts: return "SCHEDULE: [EMPTY] No upcoming appointments (Next 7 Days)."
    lines = ["REAL SCHEDULE (Use IDs for actions):"]
    for a in appts:
        p_name = a.patient.user.full_name if (a.patient and a.patient.user) else "Unknown"
        d_str = a.start_time.strftime('%Y-%m-%d')
        t_str = a.start_time.strftime('%I:%M %p')
        lines.append(f"- ID: {a.id} | {d_str} {t_str} | {p_name} | {a.treatment_type}")
    return "\n".join(lines)

def get_revenue_context(db: Session, doctor_id: int) -> str:
    paid = db.query(func.sum(models.Invoice.amount)).join(models.Appointment).filter(models.Appointment.doctor_id==doctor_id, models.Invoice.status=="paid").scalar() or 0
    pending = db.query(func.sum(models.Invoice.amount)).join(models.Appointment).filter(models.Appointment.doctor_id==doctor_id, models.Invoice.status=="pending").scalar() or 0
    recent = db.query(models.Invoice).join(models.Appointment).filter(models.Appointment.doctor_id==doctor_id).order_by(models.Invoice.id.desc()).limit(5).all()
    lines = [f"FINANCIALS:\n- Total Paid: {paid}\n- Total Pending: {pending}\n\nRECENT:"]
    for i in recent:
        p_name = i.patient.user.full_name if (i.patient and i.patient.user) else "Unknown"
        lines.append(f"- ID:{i.id} | {i.amount} | {i.status} | {p_name}")
    return "\n".join(lines)

def get_inventory_context(db: Session, hospital_id: int) -> str:
    items = db.query(models.InventoryItem).filter(models.InventoryItem.hospital_id == hospital_id).all()
    if not items: return "INVENTORY: [EMPTY]"
    lines = ["STOCK LEVELS:"]
    for i in items: lines.append(f"- {i.name}: {i.quantity} {i.unit}")
    return "\n".join(lines)

def get_casetracking_context(db: Session, doctor_id: int, query: str) -> str:
    recs = db.query(models.MedicalRecord).filter(models.MedicalRecord.doctor_id == doctor_id).order_by(models.MedicalRecord.date.desc()).limit(5).all()
    if not recs: return "RECORDS: [EMPTY]"
    lines = ["RECENT HISTORY:"]
    for r in recs:
        p_name = r.patient.user.full_name if r.patient else "Unknown"
        lines.append(f"- {r.date.strftime('%Y-%m-%d')}: {p_name} | {r.diagnosis}")
    return "\n".join(lines)

def get_patient_booking_context(db: Session) -> str:
    return "Patient Context Loaded."

# ==============================================================================
# 3. ROUTER & PROMPTS
# ==============================================================================
@router.post("/router")
async def route_agent(
    request: AgentRequest, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
):
    try:
        agent = request.role.lower().replace(" ", "")
        today = datetime.now().strftime("%Y-%m-%d")

        # --- PATIENT WIZARD ---
        if agent == "patient_booking":
            instr = "You are a Booking Wizard. Collect Hospital -> Doctor -> Date -> Time -> Reason. Output [STATE] tags."
            context_data = get_patient_booking_context(db)
            full_prompt = f"<|system|>\n{instr}\nDATA:\n{context_data}<|end|>\n"
            for msg in request.history[-6:]: full_prompt += f"<|{msg['role']}|>\n{msg['text']}<|end|>\n"
            full_prompt += f"<|user|>\n{request.user_query}<|end|>\n<|assistant|>"
            res = llm_client.generate_response(full_prompt)
            if "ACTION:" in res:
                 match = re.search(r"ACTION:.*", res)
                 if match: return {"response": execute_action(db, 0, agent, match.group(0), user.id), "agent": agent}
            return {"response": res, "agent": agent}

        # --- DOCTOR AGENTS ---
        doctor = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
        if not doctor: return {"response": "Error: Doctor profile not found."}

        context_data = ""
        instr = ""
        STRICT_RULES = "CRITICAL: TRUST DATA. IF EMPTY, SAY EMPTY. NO HALLUCINATIONS."

        if agent == "appointment":
            context_data = get_appointment_context(db, doctor.id)
            instr = (
                f"You are a Medical Assistant. TODAY: {today}\n"
                "DATA:\n{context_data}\n\n"
                "GOALS:\n"
                "1. ANSWER QUESTIONS: If user asks 'Find slots' or 'Show schedule', use DATA. If empty, say 'No appointments'.\n"
                "2. EXECUTE COMMANDS: If user asks to 'Book' or 'Cancel', USE TOOLS.\n"
                "   - CANCEL: Find ID in DATA. Output: ACTION: CANCEL | [ID]\n"
                "   - BOOK: Output: ACTION: BOOK | YYYY-MM-DD | HH:MM AM/PM | Name | Reason\n"
                "3. Do NOT output 'ACTION' for simple questions. Just chat."
            )
        elif agent == "revenue":
            context_data = get_revenue_context(db, doctor.id)
            instr = (
                f"You are a Finance Assistant. {STRICT_RULES}\n"
                "DATA:\n{context_data}\n"
                "TOOLS:\n"
                "- UPDATE: ACTION: UPDATE_INVOICE | ID | paid/cancelled"
            )
        elif agent == "inventory":
            context_data = get_inventory_context(db, doctor.hospital_id)
            instr = (
                f"You are an Inventory Assistant. {STRICT_RULES}\n"
                "DATA:\n{context_data}\n"
                "TOOLS:\n"
                "- UPDATE: ACTION: UPDATE_STOCK | ItemName | Qty"
            )
        elif agent == "casetracking":
            context_data = get_casetracking_context(db, doctor.id, request.user_query)
            instr = (
                f"You are a Clinical Assistant. {STRICT_RULES}\n"
                "DATA:\n{context_data}\n"
                "TOOLS:\n"
                "- ADD: ACTION: ADD_RECORD | PatientName | Diagnosis | Prescription"
            )

        full_prompt = f"<|system|>\n{instr}\n<|end|>\n"
        for msg in request.history[-4:]:
             role = "user" if msg['role'] == "user" else "assistant"
             full_prompt += f"<|{role}|>\n{msg['text']}<|end|>\n"
        full_prompt += f"<|user|>\n{request.user_query}<|end|>\n<|assistant|>"

        res = llm_client.generate_response(full_prompt)
        
        if "ACTION:" in res:
             match = re.search(r"ACTION:.*", res)
             if match: return {"response": execute_action(db, doctor.id, agent, match.group(0), user.id), "agent": agent}

        return {"response": res, "agent": agent}

    except Exception as e: return {"response": f"System Error: {str(e)}"}
