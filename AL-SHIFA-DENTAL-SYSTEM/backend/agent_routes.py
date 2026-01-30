from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_
from datetime import datetime, timedelta
import logging
import re
import json
from dependencies import get_current_user, get_db
import models

# --- NOTIFICATION SERVICE ---
try:
    from notifications.service import NotificationService
    notifier = NotificationService()
except ImportError:
    logging.warning("Notification Service not found. Skipping notifications.")
    notifier = None

router = APIRouter(prefix="/agent", tags=["AI Agents"])

class AgentRequest(BaseModel):
    user_query: str
    role: str
    history: list[dict] = []

# =============================================================================
# SHARED HELPERS
# =============================================================================

def send_notification(patient_email: str, subject: str, message: str):
    """Helper to send email safely without crashing the agent"""
    if notifier and patient_email:
        try:
            notifier.notify_email(patient_email, subject, message)
        except Exception as e:
            logging.error(f"Failed to send notification: {e}")

def auto_deduct_stock(db: Session, hospital_id: int, treatment_name: str):
    """Smartly deducts inventory based on treatment name"""
    logs = []
    consumables = ["Gloves", "Masks", "Dental Bibs", "Saliva Ejectors"]
    for c_name in consumables:
        item = db.query(models.InventoryItem).filter(
            models.InventoryItem.hospital_id == hospital_id,
            models.InventoryItem.name.ilike(f"%{c_name}%")
        ).first()
        if item and item.quantity > 0:
            item.quantity -= 1
            logs.append(f"-1 {item.name}")

    keywords = {
        "Root Canal": ["RCT", "Files", "Gutta", "Paper Points"],
        "Extraction": ["Suture", "Gauze", "Forceps", "Elevator"],
        "Implant": ["Implant", "Screw", "Drill"],
        "Filling": ["Composite", "Etchant", "Bonding"],
        "Whitening": ["Bleaching", "Gel"]
    }
    for key, search_terms in keywords.items():
        if key.lower() in treatment_name.lower():
            for term in search_terms:
                target = db.query(models.InventoryItem).filter(
                    models.InventoryItem.hospital_id == hospital_id,
                    models.InventoryItem.name.ilike(f"%{term}%")
                ).first()
                if target and target.quantity > 0:
                    target.quantity -= 1
                    logs.append(f"-1 {target.name}")
    db.commit()
    return ", ".join(logs) if logs else "No stock deducted"

def get_smart_slots(db: Session, doctor_id: int, date_str: str):
    doc = db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()
    start_time, end_time, duration = "09:00", "17:00", 30
    if doc and doc.scheduling_config:
        try:
            config = json.loads(doc.scheduling_config)
            start_time = config.get("work_start_time", "09:00")
            end_time = config.get("work_end_time", "17:00")
            duration = int(config.get("slot_duration", 30))
        except: pass

    try: selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except: return []

    now = datetime.now()
    start_dt = datetime.combine(selected_date, datetime.strptime(start_time, "%H:%M").time())
    end_dt = datetime.combine(selected_date, datetime.strptime(end_time, "%H:%M").time())
    
    slots = []
    curr = start_dt
    while curr < end_dt:
        slots.append(curr)
        curr += timedelta(minutes=duration)

    if selected_date == now.date():
        slots = [s for s in slots if s > now + timedelta(minutes=15)]

    booked = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == doctor_id, 
        models.Appointment.status.in_(["confirmed", "pending", "checked-in", "in-progress"]), 
        func.date(models.Appointment.start_time) == selected_date
    ).all()
    booked_times = {b.start_time for b in booked}
    
    return [s.strftime("%I:%M %p") for s in slots if s not in booked_times]

def auto_maintain_appointments(db: Session, doctor_id: int):
    now = datetime.now()
    # Auto-Cancel
    expired = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == doctor_id, 
        models.Appointment.status.in_(["confirmed", "pending"]), 
        models.Appointment.end_time < now
    ).all()
    
    for appt in expired:
        appt.status = "cancelled"
        appt.notes = (appt.notes or "") + " [Auto-Cancelled]"
        db.query(models.Invoice).filter(models.Invoice.appointment_id == appt.id, models.Invoice.status == "pending").delete()

    # Auto-Complete
    stale_limit = now - timedelta(hours=4)
    stale = db.query(models.Appointment).filter(models.Appointment.doctor_id == doctor_id, models.Appointment.status == "in_progress", models.Appointment.start_time < stale_limit).all()
    for appt in stale:
        appt.status = "completed"
        appt.notes = (appt.notes or "") + " [Auto-Completed]"
        try:
            doc = db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()
            if appt.treatment_type: auto_deduct_stock(db, doc.hospital_id, appt.treatment_type)
        except: pass
    if expired or stale: db.commit()

# =============================================================================
# 1. INVENTORY AGENT
# =============================================================================
def handle_inventory_logic(db: Session, doctor_id: int, query: str):
    q_norm = query.lower().strip()
    doc = db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()
    hid = doc.hospital_id if doc else 1

    if q_norm in ["menu", "hi", "hello", "start", "main menu"]:
        return {"response": "📦 **Inventory Agent**\nTrack stock, log usage, and manage supplies.", "options": ["Check Low Stock", "Stock Status", "Log Usage", "Add Stock"]}

    if q_norm == "stock status" or q_norm == "check low stock":
        items = db.query(models.InventoryItem).filter(models.InventoryItem.hospital_id == hid).all()
        low = [i for i in items if i.quantity <= getattr(i, "min_threshold", 10)]
        msg = f"📦 **Inventory Status ({len(items)} Items)**\n"
        msg += "⚠️ **LOW STOCK:**\n" + "\n".join([f"- {i.name}: {i.quantity} {i.unit}" for i in low]) if low else "✅ All stock healthy."
        return {"response": msg, "options": ["Log Usage", "Add Stock", "Main Menu"]}

    if q_norm == "log usage":
        items = db.query(models.InventoryItem).filter(models.InventoryItem.hospital_id == hid).order_by(models.InventoryItem.name).limit(20).all()
        return {"response": "Select Item Used:", "options": [f"Used: {i.name} | ID:{i.id}" for i in items] + ["Main Menu"]}

    if q_norm.startswith("used:"):
        parts = q_norm.split(" | id:")
        if len(parts) < 2: return {"response": "Error parsing item.", "options": ["Log Usage"]}
        name = parts[0].replace("used: ", "")
        iid = int(parts[1])
        return {"response": f"Quantity used?", "options": [f"Use 1 | ID:{iid}", f"Use 5 | ID:{iid}", f"Use 10 | ID:{iid}"]}

    if q_norm.startswith("use "):
        try:
            qty = int(q_norm.split(" | ")[0].replace("use ", ""))
            iid = int(re.search(r"id:(\d+)", q_norm).group(1))
            item = db.query(models.InventoryItem).filter(models.InventoryItem.id == iid).first()
            if item:
                item.quantity = max(0, item.quantity - qty)
                db.commit()
                return {"response": f"✅ Logged. **{item.name}**: {item.quantity} remaining.", "options": ["Log Another", "Stock Status"]}
        except: pass
    
    if q_norm == "add stock":
        items = db.query(models.InventoryItem).filter(models.InventoryItem.hospital_id == hid).order_by(models.InventoryItem.quantity).limit(20).all()
        return {"response": "Select Item to Restock:", "options": [f"Add: {i.name} | ID:{i.id}" for i in items] + ["Main Menu"]}

    if q_norm.startswith("add:"):
        iid = int(re.search(r"id:(\d+)", q_norm).group(1))
        return {"response": "Qty to add?", "options": [f"Add +10 | ID:{iid}", f"Add +50 | ID:{iid}", f"Add +100 | ID:{iid}"]}

    if q_norm.startswith("add +"):
        qty = int(q_norm.split(" | ")[0].replace("add +", ""))
        iid = int(re.search(r"id:(\d+)", q_norm).group(1))
        item = db.query(models.InventoryItem).filter(models.InventoryItem.id == iid).first()
        item.quantity += qty; db.commit()
        return {"response": f"✅ Stock Updated. **{item.name}**: {item.quantity}", "options": ["Stock Status"]}

    return {"response": "Unknown command.", "options": ["Main Menu"]}

# =============================================================================
# 2. REVENUE AGENT
# =============================================================================
def handle_revenue_logic(db: Session, doctor_id: int, query: str):
    q_norm = query.lower().strip()
    now = datetime.now()
    
    treatments = db.query(models.Treatment).filter(models.Treatment.doctor_id == doctor_id).all()
    RC = {t.name: t.cost for t in treatments}
    if not RC: RC = {"Consultation": 500}

    if q_norm in ["menu", "hi", "hello", "start", "main menu"]: 
        return {"response": "💰 **Revenue Agent**\nTrack earnings, create invoices, and monitor payments.", "options": ["Create New Invoice", "Show Unpaid Bills", "Daily Report"]}
    
    if q_norm == "daily report":
        s = now.replace(hour=0,minute=0)
        t = db.query(func.sum(models.Invoice.amount)).filter(models.Invoice.created_at>=s).scalar() or 0
        paid = db.query(func.sum(models.Invoice.amount)).filter(models.Invoice.created_at>=s, models.Invoice.status=="paid").scalar() or 0
        return {"response": f"📊 **Daily Report:**\n💰 Collected: ₹{paid}\n⏳ Pending: ₹{t-paid}", "options": ["Main Menu"]}

    if q_norm == "create new invoice":
        appts = db.query(models.Appointment).filter(models.Appointment.doctor_id==doctor_id).order_by(desc(models.Appointment.start_time)).limit(10).all()
        return {"response": "Select patient:", "options": [f"Bill: {a.patient.user.full_name} (ID:{a.patient_id})" for a in appts] + ["Main Menu"]}
    
    if q_norm.startswith("bill:"):
        pid = re.search(r"\(id:(\d+)\)", q_norm).group(1)
        return {"response": "Select Procedure:", "options": [f"Add: {n} - ₹{p} | P:{pid}" for n, p in RC.items()]}
    
    if q_norm.startswith("add:"):
        p = q_norm.split(" | p:")
        n, v = p[0].replace("add: ", "").split(" - ₹")
        i = models.Invoice(patient_id=int(p[1]), amount=float(v), status="pending", created_at=now, details=n)
        db.add(i); db.commit()
        return {"response": f"✅ Invoice Created: {n} (₹{v})", "options": [f"Pay Cash | ID:{i.id}", f"Pay Online | ID:{i.id}", "Main Menu"]}
    
    if q_norm == "show unpaid bills":
        u = db.query(models.Invoice).filter(models.Invoice.status=="pending").all()
        if not u: return {"response": "✅ No unpaid bills!", "options": ["Main Menu"]}
        return {"response": "Unpaid Bills:", "options": [f"Pay: {i.patient.user.full_name} (₹{i.amount}) | ID:{i.id}" for i in u]}
    
    if q_norm.startswith("pay:"): 
        return {"response": "Select Mode:", "options": [f"Pay Cash | ID:{re.search(r'\| id:(\d+)', q_norm).group(1)}", f"Pay Online | ID:{re.search(r'\| id:(\d+)', q_norm).group(1)}"]}
    
    if q_norm.startswith("pay cash") or q_norm.startswith("pay online"):
        i = db.query(models.Invoice).filter(models.Invoice.id==int(re.search(r"\| id:(\d+)", q_norm).group(1))).first()
        if i:
            i.status="paid"
            i.details += " [Mode: " + ("Cash" if "cash" in q_norm else "Online") + "]"
            db.commit()
            return {"response": "✅ Payment Recorded.", "options": ["Daily Report"]}

    return {"response": "Unknown command.", "options": ["Main Menu"]}

# =============================================================================
# 3. APPOINTMENT AGENT (WITH NOTIFICATIONS)
# =============================================================================
def handle_appointment_logic(db: Session, doctor_id: int, query: str):
    auto_maintain_appointments(db, doctor_id)
    q_norm = query.lower().strip()
    now = datetime.now()
    
    treatments = db.query(models.Treatment).filter(models.Treatment.doctor_id == doctor_id).all()
    REASONS = [t.name for t in treatments] if treatments else ["Consultation"]

    if q_norm in ["menu", "hi", "hello", "start", "main menu"]: 
        return {"response": "🗓️ **Appointment Agent**\nManage bookings and schedule.", "options": ["Show Today's Schedule", "Show This Week", "Book Appointment", "Cancel Appointment"]}
    
    if "schedule" in q_norm or "today" in q_norm or "week" in q_norm:
        if "previous week" in q_norm: start, end, title = (now-timedelta(days=now.weekday()+7)).replace(hour=0,minute=0), (now-timedelta(days=now.weekday()+1)).replace(hour=23,minute=59), "Previous Week"
        elif "this week" in q_norm: start, end, title = (now-timedelta(days=now.weekday())).replace(hour=0,minute=0), (now+timedelta(days=6)).replace(hour=23,minute=59), "This Week"
        else: start, end, title = now.replace(hour=0,minute=0), now.replace(hour=23,minute=59), "Today"
        
        appts = db.query(models.Appointment).filter(models.Appointment.doctor_id==doctor_id, models.Appointment.start_time>=start, models.Appointment.start_time<=end).order_by(models.Appointment.start_time).all()
        msg = f"📅 **{title}:**\n" + ("\n".join([f"- {a.start_time.strftime('%I:%M %p')}: {a.patient.user.full_name} ({a.status} - {a.treatment_type or 'General'})" for a in appts]) if appts else "No appointments.")
        return {"response": msg, "options": ["Book Appointment", "Main Menu"]}
    
    if "book appointment" == q_norm:
        recent = db.query(models.Appointment).filter(models.Appointment.doctor_id==doctor_id).order_by(desc(models.Appointment.start_time)).limit(50).all()
        seen, btns = set(), []
        for a in recent: 
            if a.patient_id not in seen: btns.append(f"Select: {a.patient.user.full_name} (ID: {a.patient_id})"); seen.add(a.patient_id)
            if len(btns)>=5: break
        return {"response": "Select recent or **Type Patient ID**:", "options": btns + ["Main Menu"]}
    
    if q_norm.isdigit() or q_norm.startswith("id "):
        pid = int(re.sub(r"\D", "", q_norm))
        p = db.query(models.Patient).filter(models.Patient.id==pid).first()
        return {"response": f"Booking **{p.user.full_name}** (ID: {pid}). Select Date:", "options": [f"__UI_CALENDAR__|P:{pid}", "Main Menu"]} if p else {"response": "ID Not Found", "options": ["Book Appointment"]}
    
    if q_norm.startswith("select:"): 
        return {"response": f"Pick date:", "options": [f"__UI_CALENDAR__|P:{re.search(r'\(id:\s*(\d+)\)', q_norm).group(1)}", "Main Menu"]}
    
    if q_norm.startswith("calendar_date:"):
        p = q_norm.replace("calendar_date: ", "").split("|")
        slots = get_smart_slots(db, doctor_id, p[0].strip())
        return {"response": f"Slots for **{p[0]}**:", "options": [f"Confirm: {p[0]} @ {t} | {p[1].strip()}" for t in slots]}
    
    if q_norm.startswith("confirm:"):
        return {"response": "Select **Reason**:", "options": [f"Do: {r} | {q_norm.replace('confirm: ', '')}" for r in REASONS] + ["Do: Other | " + q_norm.replace('confirm: ', '')]}
    
    # --- BOOKING LOGIC (STRICT + NOTIFICATION) ---
    if q_norm.startswith("do:"):
        p = q_norm.replace("do: ", "").split(" | p:")
        reason, date_part = p[0].split(" | ")
        dt = datetime.strptime(date_part.strip().replace(" @ ", " "), "%Y-%m-%d %I:%M %p")
        
        # STRICT RULE: ONE ACTIVE APPOINTMENT
        active_appt = db.query(models.Appointment).filter(
            models.Appointment.patient_id == int(p[1]),
            models.Appointment.status.in_(["confirmed", "pending", "checked-in", "in-progress"])
        ).first()
        
        if active_appt:
            return {
                "response": f"❌ **Limit Reached**: Active appointment exists on **{active_appt.start_time.strftime('%Y-%m-%d %I:%M %p')}**.\n\nType **'Reschedule ID {active_appt.id}'**.", 
                "options": [f"Reschedule ID {active_appt.id}", f"Cancel - ID {active_appt.id}"]
            }

        # 1. Create Appointment
        new_appt = models.Appointment(
            doctor_id=doctor_id, 
            patient_id=int(p[1]), 
            start_time=dt, 
            end_time=dt+timedelta(minutes=30), 
            status="confirmed", 
            treatment_type=reason, 
            notes=f"Reason: {reason}"
        )
        db.add(new_appt)
        db.flush()
        
        # 2. Link Invoice
        trt = db.query(models.Treatment).filter(models.Treatment.name.ilike(reason), models.Treatment.doctor_id==doctor_id).first()
        cost = trt.cost if trt else 500.0
        db.add(models.Invoice(patient_id=int(p[1]), appointment_id=new_appt.id, amount=cost, status="pending", created_at=datetime.utcnow(), details=f"Appointment: {reason}"))
        db.commit()

        # 3. NOTIFICATION
        patient = db.query(models.Patient).filter(models.Patient.id == int(p[1])).first()
        if patient and patient.user.email:
            send_notification(
                patient.user.email,
                "Appointment Confirmed - Al-Shifa Dental",
                f"Dear {patient.user.full_name},\n\nYour appointment for {reason} is confirmed for {dt.strftime('%A, %d %B at %I:%M %p')}.\n\nThank you."
            )

        return {"response": f"✅ Booked for **{reason}**. Email sent.", "options": ["Show Schedule"]}
    
    # --- RESCHEDULING & MANAGEMENT ---
    if "manage" in q_norm and "id" in q_norm:
        aid = int(re.search(r"id\s*(\d+)", q_norm).group(1))
        appt = db.query(models.Appointment).filter(models.Appointment.id==aid).first()
        st = appt.status
        opts = [f"Start Appointment - ID {aid}", f"Reschedule ID {aid}", f"Cancel - ID {aid}"] if st in ["confirmed", "pending"] else \
               [f"Complete & Bill - ID {aid}"] if st=="in_progress" else ["Back"]
        return {"response": f"Managing ID {aid} ({st})", "options": opts + ["Back"]}
    
    if "reschedule" in q_norm:
        if "id" not in q_norm: return {"response": "Which appointment? (e.g., 'Reschedule ID 1')", "options": ["Show Schedule"]}
        aid = int(re.search(r"id\s*(\d+)", q_norm).group(1))
        return {"response": f"Pick new date for ID {aid}:", "options": [f"__UI_CALENDAR__|RESCHEDULE:{aid}", "Cancel Update"]}

    if "RESCHEDULE:" in q_norm:
        parts = q_norm.split("|")
        date_str = parts[0].replace("calendar_date: ", "").strip()
        aid = int(parts[1].replace("RESCHEDULE:", ""))
        slots = get_smart_slots(db, doctor_id, date_str)
        return {"response": f"New slots for **{date_str}**:", "options": [f"Move ID {aid} to {date_str} @ {t}" for t in slots]}

    if q_norm.startswith("move id"):
        match = re.search(r"move id (\d+) to (.*)", q_norm)
        if match:
            aid = int(match.group(1))
            new_time_str = match.group(2).strip()
            new_dt = datetime.strptime(new_time_str, "%Y-%m-%d @ %I:%M %p")
            
            if db.query(models.Appointment).filter(models.Appointment.doctor_id==doctor_id, models.Appointment.start_time==new_dt, models.Appointment.status!="cancelled").first():
                return {"response": "❌ Slot taken.", "options": ["Show Schedule"]}

            appt = db.query(models.Appointment).filter(models.Appointment.id==aid).first()
            if appt:
                appt.start_time = new_dt
                appt.end_time = new_dt + timedelta(minutes=30)
                db.commit()
                # NOTIFICATION
                if appt.patient.user.email:
                    send_notification(appt.patient.user.email, "Appointment Rescheduled", f"Your appointment has been moved to {new_time_str}.")
                return {"response": f"✅ Rescheduled to **{new_time_str}**.", "options": ["Show Schedule"]}

    if "start appointment" in q_norm:
        db.query(models.Appointment).filter(models.Appointment.id==int(re.search(r"id\s*(\d+)", q_norm).group(1))).update({"status": "in_progress"}); db.commit()
        return {"response": "✅ Started.", "options": ["Show Today's Schedule"]}
    
    if "cancel" in q_norm:
        aid = int(re.search(r"id\s*(\d+)", q_norm).group(1))
        a=db.query(models.Appointment).filter(models.Appointment.id==aid).first()
        a.status="cancelled"
        db.query(models.Invoice).filter(models.Invoice.appointment_id==aid, models.Invoice.status=="pending").delete()
        db.commit()
        # NOTIFICATION
        if a.patient.user.email:
            send_notification(a.patient.user.email, "Appointment Cancelled", f"Your appointment on {a.start_time.strftime('%Y-%m-%d')} has been cancelled.")
        return {"response": f"✅ Cancelled ID {aid}.", "options": ["Show Schedule"]}

    # --- COMPLETION ---
    if "complete & bill" in q_norm:
        aid = int(re.search(r"id\s*(\d+)", q_norm).group(1))
        a = db.query(models.Appointment).filter(models.Appointment.id==aid).first()
        a.status = "completed"
        
        doc = db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()
        stock_msg = auto_deduct_stock(db, doc.hospital_id, a.treatment_type or "")
        
        inv = db.query(models.Invoice).filter(models.Invoice.appointment_id == aid).first()
        bill_msg = ""
        if inv:
            inv.status = "paid"; inv.details += " [Auto-Paid: Cash]"; bill_msg = f"Revenue: ₹{inv.amount}"
        else:
            cost = 500.0
            db.add(models.Invoice(patient_id=a.patient_id, appointment_id=aid, amount=cost, status="paid", created_at=now, details=f"{a.treatment_type} [Auto-Paid: Cash]"))
            bill_msg = f"Revenue: ₹{cost}"
        
        db.commit()
        return {"response": f"✅ Completed.\n💰 {bill_msg}\n📦 Stock: {stock_msg}", "options": ["Show Today's Schedule"]}

    return {"response": "Error.", "options": ["Main Menu"]}

# =============================================================================
# 4. CASE TRACKING AGENT (WITH PRESCRIPTIONS)
# =============================================================================
def handle_case_tracking_logic(db: Session, doctor_id: int, query: str):
    q_norm = query.lower().strip()
    if q_norm in ["menu", "hi", "hello", "start", "main menu"]:
        return {"response": "🩺 **Case Tracking Agent**\nView records or write prescriptions.", "options": ["Search Patient", "Recent Patients"]}

    if q_norm == "recent patients":
        appts = db.query(models.Appointment).filter(models.Appointment.doctor_id==doctor_id).order_by(desc(models.Appointment.start_time)).limit(5).all()
        return {"response": "Recent Patients:", "options": [f"View ID {a.patient.id} ({a.patient.user.full_name})" for a in appts] + ["Main Menu"]}

    if q_norm.startswith("search") or q_norm == "search patient":
        return {"response": "Type **Patient ID** (e.g., 'ID 1'):", "options": ["Main Menu"]}

    if "view id" in q_norm or "id " in q_norm or q_norm.isdigit():
        pid = int(re.sub(r"\D", "", q_norm))
        p = db.query(models.Patient).filter(models.Patient.id == pid).first()
        if not p: return {"response": "❌ Patient not found.", "options": ["Search Patient"]}
        
        info = f"👤 **{p.user.full_name}** (ID: {pid})\n"
        info += f"🎂 DOB: {p.date_of_birth} | 🩸 History: {p.medical_history or 'None'}\n"
        return {"response": info, "options": [f"History | ID:{pid}", f"Prescriptions | ID:{pid}", f"Write Rx | ID:{pid}", "Main Menu"]}

    if "write rx" in q_norm:
        pid = int(re.search(r"id:(\d+)", q_norm).group(1))
        return {"response": f"Format: **Prescribe: Meds | Dosage | Instr | ID:{pid}**\nExample: *Prescribe: Amoxicillin | 500mg | 3x daily | ID:{pid}*"}

    if q_norm.startswith("prescribe:"):
        # Parse: Prescribe: Amoxicillin | 500mg | 3x daily | ID:1
        try:
            content = q_norm.replace("prescribe: ", "")
            parts = [p.strip() for p in content.split("|")]
            
            med = parts[0]
            dose = parts[1] if len(parts)>1 else "As directed"
            instr = parts[2] if len(parts)>2 else "None"
            pid_str = parts[3] if len(parts)>3 else ""
            
            pid = int(re.search(r"(\d+)", pid_str).group(1))
            
            rx = models.Prescription(
                patient_id=pid,
                medication=med,
                dosage=dose,
                instructions=instr,
                created_at=datetime.utcnow()
            )
            db.add(rx)
            db.commit()
            return {"response": f"✅ Prescription Saved:\n💊 {med} - {dose}", "options": [f"Prescriptions | ID:{pid}", "Main Menu"]}
        except Exception as e:
            return {"response": f"❌ Error: Use format **Meds | Dose | Instr | ID:X**", "options": ["Main Menu"]}

    if " | id:" in q_norm:
        pid = int(re.search(r"id:(\d+)", q_norm).group(1))
        
        if q_norm.startswith("history"):
            appts = db.query(models.Appointment).filter(models.Appointment.patient_id==pid).order_by(desc(models.Appointment.start_time)).limit(5).all()
            msg = "🗓️ **History:**\n" + "\n".join([f"- {a.start_time.strftime('%Y-%m-%d')}: {a.treatment_type} ({a.status})" for a in appts])
            return {"response": msg or "No history.", "options": [f"Prescriptions | ID:{pid}", "Main Menu"]}

        if q_norm.startswith("prescriptions"):
            pre = db.query(models.Prescription).filter(models.Prescription.patient_id==pid).order_by(desc(models.Prescription.created_at)).limit(5).all()
            msg = "💊 **Prescriptions:**\n" + "\n".join([f"- {p.medication} ({p.dosage})" for p in pre])
            return {"response": msg or "No prescriptions.", "options": [f"Write Rx | ID:{pid}", "Main Menu"]}

    return {"response": "Unknown command.", "options": ["Main Menu"]}

@router.post("/router")
async def route_agent(request: AgentRequest, user: models.User=Depends(get_current_user), db: Session=Depends(get_db)):
    try:
        agent = request.role.lower().replace(" ", "")
        doc = db.query(models.Doctor).filter(models.Doctor.user_id==user.id).first()
        if not doc: return {"response": "Error: Doctor profile not found.", "options": []}
        
        if agent=="appointment": return handle_appointment_logic(db, doc.id, request.user_query)
        if agent=="revenue": return handle_revenue_logic(db, doc.id, request.user_query)
        if agent=="inventory": return handle_inventory_logic(db, doc.id, request.user_query)
        if agent=="casetracking": return handle_case_tracking_logic(db, doc.id, request.user_query)
        
        return {"response": "Ready.", "options": ["Main Menu"]}
    except Exception as e: 
        logging.error(f"Agent Error: {e}")
        return {"response": f"Error: {str(e)}", "options": ["Retry"]}
