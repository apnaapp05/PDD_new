from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
import logging
import re
import json
from dependencies import get_current_user, get_db
import models

router = APIRouter(prefix="/agent", tags=["AI Agents"])

class AgentRequest(BaseModel):
    user_query: str
    role: str
    history: list[dict] = []

# =============================================================================
# SHARED HELPERS
# =============================================================================

def auto_deduct_stock(db: Session, hospital_id: int, treatment_name: str):
    """Smartly deducts inventory based on treatment name"""
    logs = []
    
    # 1. ALWAYS DEDUCT CONSUMABLES
    consumables = ["Gloves", "Masks", "Dental Bibs", "Saliva Ejectors"]
    for c_name in consumables:
        item = db.query(models.InventoryItem).filter(
            models.InventoryItem.hospital_id == hospital_id,
            models.InventoryItem.name.ilike(f"%{c_name}%")
        ).first()
        
        if item and item.quantity > 0:
            item.quantity -= 1
            logs.append(f"-1 {item.name}")

    # 2. SPECIFIC DEDUCTION
    keywords = {
        "Root Canal": ["RCT", "Files", "Gutta", "Paper Points"],
        "Extraction": ["Suture", "Gauze", "Forceps", "Elevator"],
        "Implant": ["Implant", "Screw", "Drill"],
        "Filling": ["Composite", "Etchant", "Bonding", "Applicator"],
        "Whitening": ["Bleaching", "Gel", "Barrier"]
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
    # 1. Fetch Doctor Settings
    doc = db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()
    
    # Defaults
    start_time = "09:00"
    end_time = "17:00"
    duration = 30
    
    # Parse Config if exists
    if doc and doc.scheduling_config:
        try:
            config = json.loads(doc.scheduling_config)
            start_time = config.get("work_start_time", "09:00")
            end_time = config.get("work_end_time", "17:00")
            duration = int(config.get("slot_duration", 30))
        except: pass

    # 2. Generate Slots
    try:
        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except:
        return []

    now = datetime.now()
    
    start_dt = datetime.combine(selected_date, datetime.strptime(start_time, "%H:%M").time())
    end_dt = datetime.combine(selected_date, datetime.strptime(end_time, "%H:%M").time())
    
    slots = []
    curr = start_dt
    while curr < end_dt:
        slots.append(curr)
        curr += timedelta(minutes=duration)

    # 3. Filter Past Slots (only if date is today)
    if selected_date == now.date():
        slots = [s for s in slots if s > now + timedelta(minutes=15)]

    # 4. Filter Booked Slots
    booked = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == doctor_id,
        models.Appointment.status.in_(["confirmed", "pending", "checked-in", "in-progress"]),
        func.date(models.Appointment.start_time) == selected_date
    ).all()
    
    booked_times = {b.start_time for b in booked}
    
    return [s.strftime("%I:%M %p") for s in slots if s not in booked_times]

def auto_maintain_appointments(db: Session, doctor_id: int):
    now = datetime.now()
    
    # 1. AUTO-CANCEL: Confirmed/Pending apps passed their end_time (Not Started)
    expired = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == doctor_id, 
        models.Appointment.status.in_(["confirmed", "pending"]), 
        models.Appointment.end_time < now
    ).all()
    
    for appt in expired:
        appt.status = "cancelled"
        appt.notes = (appt.notes or "") + " [Auto-Cancelled]"
        # DELETE pending invoice (Revenue won't be affected)
        db.query(models.Invoice).filter(
            models.Invoice.patient_id == appt.patient_id, 
            models.Invoice.status == "pending", 
            func.date(models.Invoice.created_at) == appt.start_time.date()
        ).delete(synchronize_session=False)

    # 2. AUTO-COMPLETE: In-Progress apps left open at end of day (stale > 4 hours)
    stale_limit = now - timedelta(hours=4)
    stale = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == doctor_id, 
        models.Appointment.status == "in_progress", 
        models.Appointment.start_time < stale_limit
    ).all()
    
    for appt in stale:
        appt.status = "completed"
        appt.notes = (appt.notes or "") + " [Auto-Completed]"
        # Leave revenue as pending (doctor must verify payment) OR auto-pay if desired
        # Keeping it safe for now.
        
        # Inventory Deduction:
        try:
            doc = db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()
            hid = doc.hospital_id if doc else 1
            if appt.treatment_type:
                auto_deduct_stock(db, hid, appt.treatment_type)
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
        return {"response": "Inventory Agent Active.", "options": ["Check Low Stock", "Stock Status", "Log Usage", "Add Stock"]}

    if q_norm == "stock status" or q_norm == "check low stock":
        items = db.query(models.InventoryItem).filter(models.InventoryItem.hospital_id == hid).all()
        # Use 'min_threshold' or 'threshold' depending on model, try catch
        low = []
        for i in items:
            thresh = getattr(i, "min_threshold", getattr(i, "threshold", 10))
            if i.quantity <= thresh: low.append(i)
        
        msg = f"📦 **Inventory Status ({len(items)} Items)**\n"
        if low:
            msg += "⚠️ **LOW STOCK ALERT:**\n" + "\n".join([f"- {i.name}: **{i.quantity} {i.unit}**" for i in low])
        else:
            msg += "✅ All stock levels healthy."
            
        return {"response": msg, "options": ["Log Usage", "Add Stock", "Main Menu"]}

    if q_norm == "log usage":
        items = db.query(models.InventoryItem).filter(models.InventoryItem.hospital_id == hid).order_by(models.InventoryItem.name).all()
        return {"response": "Select Item Used:", "options": [f"Used: {i.name} | ID:{i.id}" for i in items] + ["Main Menu"]}

    if q_norm.startswith("used:"):
        parts = q_norm.split(" | id:")
        name = parts[0].replace("used: ", "")
        iid = int(parts[1])
        return {"response": f"How many **{name}**?", "options": [f"Use 1 | ID:{iid}", f"Use 5 | ID:{iid}", f"Use 10 | ID:{iid}"]}

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
        items = db.query(models.InventoryItem).filter(models.InventoryItem.hospital_id == hid).order_by(models.InventoryItem.quantity).all()
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

    if q_norm in ["menu", "hi", "hello", "start", "main menu"]: return {"response": "Revenue Agent Active.", "options": ["Create New Invoice", "Show Unpaid Bills", "Daily Report", "Weekly Report"]}
    
    if q_norm == "daily report":
        s = now.replace(hour=0,minute=0)
        t = db.query(func.sum(models.Invoice.amount)).filter(models.Invoice.created_at>=s).scalar() or 0
        c = db.query(func.sum(models.Invoice.amount)).filter(models.Invoice.created_at>=s, models.Invoice.status=="paid", models.Invoice.details.like("%[Mode: Cash]%")).scalar() or 0
        o = db.query(func.sum(models.Invoice.amount)).filter(models.Invoice.created_at>=s, models.Invoice.status=="paid", models.Invoice.details.like("%[Mode: Online]%")).scalar() or 0
        return {"response": f"📊 **Today:**\n💰 Total Revenue: ₹{c+o}\n⏳ Pending: ₹{t-(c+o)}", "options": ["Main Menu"]}

    if q_norm == "create new invoice":
        appts = db.query(models.Appointment).filter(models.Appointment.doctor_id==doctor_id, models.Appointment.start_time>=now.replace(hour=0,minute=0)).all()
        return {"response": "Select patient or Type ID:", "options": [f"Bill: {a.patient.user.full_name} (ID:{a.patient_id})" for a in appts] + ["Main Menu"]}
    
    if q_norm.startswith("bill:"):
        pid = re.search(r"\(id:(\d+)\)", q_norm).group(1)
        return {"response": "Select Procedure:", "options": [f"Add: {n} - ₹{p} | P:{pid}" for n, p in RC.items()]}
    
    if q_norm.startswith("add:"):
        p = q_norm.split(" | p:")
        n, v = p[0].replace("add: ", "").split(" - ₹")
        i = models.Invoice(patient_id=int(p[1]), amount=float(v), status="pending", created_at=now, details=n)
        db.add(i); db.commit()
        return {"response": f"✅ Bill Created: {n}", "options": [f"Cash | ID:{i.id}", f"Online | ID:{i.id}", "Later"]}
    
    if q_norm == "show unpaid bills":
        u = db.query(models.Invoice).filter(models.Invoice.status=="pending").all()
        return {"response": "Unpaid Bills:", "options": [f"Pay: {i.patient.user.full_name} (₹{i.amount}) | ID:{i.id}" for i in u] + ["Main Menu"]}
    
    if q_norm.startswith("pay:"): return {"response": "Mode?", "options": [f"Cash | ID:{re.search(r'\| id:(\d+)', q_norm).group(1)}", f"Online | ID:{re.search(r'\| id:(\d+)', q_norm).group(1)}"]}
    
    if q_norm.startswith("cash") or q_norm.startswith("online"):
        i = db.query(models.Invoice).filter(models.Invoice.id==int(re.search(r"\| id:(\d+)", q_norm).group(1))).first()
        i.status="paid"; i.details+=f" [Mode: {'Cash' if 'cash' in q_norm else 'Online'}]"; db.commit()
        return {"response": "✅ Paid.", "options": ["Daily Report"]}

    return {"response": "Unknown command.", "options": ["Main Menu"]}

# =============================================================================
# 3. APPOINTMENT AGENT
# =============================================================================
def handle_appointment_logic(db: Session, doctor_id: int, query: str):
    auto_maintain_appointments(db, doctor_id)
    q_norm = query.lower().strip()
    now = datetime.now()
    
    treatments = db.query(models.Treatment).filter(models.Treatment.doctor_id == doctor_id).all()
    REASONS = [t.name for t in treatments] if treatments else ["Consultation"]

    if q_norm in ["menu", "hi", "hello", "start", "main menu"]: 
        return {"response": "Hello, Doctor. Select an action:", "options": ["Show Today's Schedule", "Show This Week", "Show Previous Week", "Book Appointment", "Reschedule Appointment", "Cancel Appointment"]}
    
    if "schedule" in q_norm or "today" in q_norm or "week" in q_norm:
        if "previous week" in q_norm: start, end, title, stats = (now-timedelta(days=now.weekday()+7)).replace(hour=0,minute=0), (now-timedelta(days=now.weekday()+1)).replace(hour=23,minute=59), "Previous Week", ["completed", "cancelled", "confirmed"]
        elif "this week" in q_norm: start, end, title, stats = (now-timedelta(days=now.weekday())).replace(hour=0,minute=0), (now+timedelta(days=6)).replace(hour=23,minute=59), "This Week", ["confirmed", "pending", "checked-in", "in_progress", "completed"]
        else: start, end, title, stats = now.replace(hour=0,minute=0), now.replace(hour=23,minute=59), "Today", ["confirmed", "pending", "checked-in", "in_progress"]
        appts = db.query(models.Appointment).filter(models.Appointment.doctor_id==doctor_id, models.Appointment.start_time>=start, models.Appointment.start_time<=end, models.Appointment.status.in_(stats)).order_by(models.Appointment.start_time).all()
        msg = f"📅 **{title}:**\n" + ("\n".join([f"- {a.start_time.strftime('%I:%M %p')}: {a.patient.user.full_name} ({a.status.upper()} - {a.treatment_type or 'General'})" for a in appts]) if appts else "No records.")
        return {"response": msg, "options": ["Show Today", "Show This Week", "Show Previous Week", "Book Appointment", "Main Menu"]}
    
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
        p = q_norm.replace("confirm: ", "").split("| p:")
        # Check double booking
        return {"response": "Select **Reason**:", "options": [f"Do: {r} | {q_norm.replace('confirm: ', '')}" for r in REASONS] + ["Do: Other | " + q_norm.replace('confirm: ', '')]}
    
    # --- BOOKING & BILLING LOGIC (FIXED) ---
    if q_norm.startswith("do:"):
        p = q_norm.replace("do: ", "").split(" | p:")
        reason, date_part = p[0].split(" | ")
        dt = datetime.strptime(date_part.strip().replace(" @ ", " "), "%Y-%m-%d %I:%M %p")
        
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
        db.flush() # <--- CRITICAL: Generates the ID
        
        # 2. Get Cost
        trt = db.query(models.Treatment).filter(models.Treatment.name.ilike(reason), models.Treatment.doctor_id==doctor_id).first()
        cost = trt.cost if trt else 500.0
        
        # 3. Create Invoice LINKED to Appointment (Like Patient Portal)
        new_inv = models.Invoice(
            patient_id=int(p[1]),
            appointment_id=new_appt.id, # <--- RESTORED LINK
            amount=cost,
            status="pending",
            created_at=datetime.utcnow(),
            details=f"Appointment: {reason}"
        )
        db.add(new_inv)
        db.commit()
        
        return {"response": f"✅ Booked for **{reason}**. Bill Created: ₹{cost}", "options": ["Show Schedule"]}
    
    # Manage Logic
    if "manage" in q_norm and "id" in q_norm:
        aid = int(re.search(r"id\s*(\d+)", q_norm).group(1))
        appt = db.query(models.Appointment).filter(models.Appointment.id==aid).first()
        st = appt.status
        opts = [f"Start Appointment - ID {aid}", f"Cancel - ID {aid}"] if st=="checked-in" else \
               [f"Start Appointment - ID {aid}", f"Mark Checked-In - ID {aid}", f"Cancel - ID {aid}"] if st=="confirmed" or st=="pending" else \
               [f"Complete & Bill - ID {aid}"] if st=="in_progress" else ["Back"]
        return {"response": f"Managing ID {aid} ({st})", "options": opts + ["Back"]}
    
    if "mark" in q_norm or "start appointment" in q_norm:
        st = "checked-in" if "checked-in" in q_norm else "in_progress"
        db.query(models.Appointment).filter(models.Appointment.id==int(re.search(r"id\s*(\d+)", q_norm).group(1))).update({"status": st})
        db.commit()
        return {"response": f"✅ Set to {st}", "options": ["Show Today's Schedule"]}
    
    if q_norm == "cancel appointment":
        appts = db.query(models.Appointment).filter(models.Appointment.doctor_id==doctor_id, models.Appointment.start_time>now, models.Appointment.status!="cancelled").all()
        return {"response": "Cancel whom?", "options": [f"Kill: {a.patient.user.full_name} - ID:{a.id}" for a in appts] + ["Main Menu"]}
    
    if q_norm.startswith("kill:") or (q_norm.startswith("cancel - id")):
        aid = int(re.search(r"id:(\d+)", q_norm).group(1)) if "id:" in q_norm else int(re.search(r"id\s*(\d+)", q_norm).group(1))
        a=db.query(models.Appointment).filter(models.Appointment.id==aid).first()
        a.status="cancelled"
        
        # Remove Invoice if unpaid (Matching by Patient + Date)
        db.query(models.Invoice).filter(models.Invoice.patient_id==a.patient_id, models.Invoice.status=="pending", func.date(models.Invoice.created_at)==a.start_time.date()).delete(synchronize_session=False)
        db.commit()
        return {"response": f"✅ Cancelled ID {aid}.", "options": ["Show Schedule"]}

    # --- COMPLETION & INVENTORY DEDUCTION ---
    if "complete & bill" in q_norm:
        aid = int(re.search(r"id\s*(\d+)", q_norm).group(1))
        a = db.query(models.Appointment).filter(models.Appointment.id==aid).first()
        
        # 1. Update Status
        a.status = "completed"
        
        # 2. Deduct Inventory
        doc = db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()
        stock_msg = auto_deduct_stock(db, doc.hospital_id, a.treatment_type or "")
        
        # 3. FINANCE: Find Linked Invoice
        inv = db.query(models.Invoice).filter(models.Invoice.appointment_id == aid).first()
        
        bill_msg = ""
        if inv:
            inv.status = "paid"
            inv.details += " [Auto-Paid: Cash]" 
            bill_msg = f"Revenue: ₹{inv.amount}"
        else:
            # Fallback if no invoice found (Create & Pay)
            cost = 500.0
            db.add(models.Invoice(
                patient_id=a.patient_id, 
                appointment_id=aid, # <--- RESTORED LINK
                amount=cost, 
                status="paid",
                created_at=now, 
                details=f"{a.treatment_type} [Auto-Paid: Cash]"
            ))
            bill_msg = f"Revenue: ₹{cost}"
        
        db.commit()
        return {"response": f"✅ Completed.\n💰 {bill_msg}\n📦 Stock: {stock_msg}", "options": ["Show Today's Schedule"]}

    return {"response": "Error.", "options": ["Main Menu"]}

@router.post("/router")
async def route_agent(request: AgentRequest, user: models.User=Depends(get_current_user), db: Session=Depends(get_db)):
    try:
        agent = request.role.lower().replace(" ", "")
        doc = db.query(models.Doctor).filter(models.Doctor.user_id==user.id).first()
        if not doc: return {"response": "Error: Doctor profile not found.", "options": []}
        
        if agent=="appointment": return handle_appointment_logic(db, doc.id, request.user_query)
        if agent=="revenue": return handle_revenue_logic(db, doc.id, request.user_query)
        if agent=="inventory": return handle_inventory_logic(db, doc.id, request.user_query)
        return {"response": "Ready.", "options": ["Main Menu"]}
    except Exception as e: 
        logging.error(f"Agent Error: {e}")
        return {"response": f"Error: {str(e)}", "options": ["Retry"]}

