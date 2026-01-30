from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
import logging
import re
from dependencies import get_current_user, get_db
import models

def auto_deduct_stock(db: Session, hospital_id: int, treatment_name: str):
    """Smartly deducts inventory based on treatment name"""
    logs = []
    
    # 1. ALWAYS DEDUCT CONSUMABLES (Gloves & Masks)
    consumables = ["Gloves", "Masks", "Dental Bibs", "Saliva Ejectors"]
    for c_name in consumables:
        # Fuzzy search for the item
        item = db.query(models.InventoryItem).filter(
            models.InventoryItem.hospital_id == hospital_id,
            models.InventoryItem.name.ilike(f"%{c_name}%")
        ).first()
        
        if item and item.quantity > 0:
            item.quantity -= 1
            logs.append(f"-1 {item.name}")

    # 2. SPECIFIC DEDUCTION (Simple keyword matching)
    # If Treatment is "Root Canal", look for "RCT" or "Files"
    keywords = {
        "Root Canal": ["RCT", "Files", "Gutta"],
        "Extraction": ["Suture", "Gauze"],
        "Implant": ["Implant", "Screw"],
        "Filling": ["Composite", "Etchant", "Bonding"]
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

router = APIRouter(prefix="/agent", tags=["AI Agents"])

class AgentRequest(BaseModel):
    user_query: str
    role: str
    history: list[dict] = []

# =============================================================================
# SHARED HELPERS
# =============================================================================
def get_smart_slots(db: Session, doctor_id: int, date_str: str):
    start_hour, end_hour, interval = 9, 17, 30
    selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    now = datetime.now()
    slots = []
    curr = datetime.combine(selected_date, datetime.min.time()).replace(hour=start_hour)
    end = datetime.combine(selected_date, datetime.min.time()).replace(hour=end_hour)
    while curr < end:
        slots.append(curr)
        curr += timedelta(minutes=interval)
    if selected_date == now.date():
        slots = [s for s in slots if s > now + timedelta(minutes=15)]
    booked = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == doctor_id,
        models.Appointment.start_time >= datetime.combine(selected_date, datetime.min.time()),
        models.Appointment.start_time <= datetime.combine(selected_date, datetime.max.time()),
        models.Appointment.status.in_(["confirmed", "pending", "checked-in", "in-progress"])
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

    # 2. AUTO-COMPLETE: In-Progress apps left open at end of day (e.g. after 8 PM or 3 hours stale)
    # Let''s use "End of Day" logic: If it''s started and time is past 11:59 PM of that day? 
    # Or simple stale check > 4 hours. Let''s do Stale > 4 hours for safety.
    stale_limit = now - timedelta(hours=4)
    stale = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == doctor_id, 
        models.Appointment.status == "in-progress", 
        models.Appointment.start_time < stale_limit
    ).all()
    
    for appt in stale:
        appt.status = "completed"
        appt.notes = (appt.notes or "") + " [Auto-Completed]"
        # Revenue is already Pending, so it stays.
        # Inventory Deduction:
        try:
            doc = db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()
            hid = doc.hospital_id if doc else 1
            if appt.treatment_type:
                auto_deduct_stock(db, hid, appt.treatment_type)
        except: pass

    if expired or stale: db.commit()

# =============================================================================
# 1. INVENTORY AGENT (Connected to Real DB)
# =============================================================================
def handle_inventory_logic(db: Session, doctor_id: int, query: str):
    q_norm = query.lower().strip()
    
    # Get Hospital ID (assuming linked via Doctor -> User -> Hospital or direct)
    # Simple fallback for now
    hosp = db.query(models.Hospital).first()
    hid = hosp.id if hosp else 1

    if q_norm in ["menu", "hi", "hello", "start", "main menu"]:
        return {"response": "Inventory Agent Active.", "options": ["Check Low Stock", "Stock Status", "Log Usage", "Add Stock"]}

    if q_norm == "stock status" or q_norm == "check low stock":
        items = db.query(models.InventoryItem).filter(models.InventoryItem.hospital_id == hid).all()
        low = [i for i in items if i.quantity <= i.min_threshold]
        
        msg = f"📦 **Inventory Status ({len(items)} Items)**\n"
        if low:
            msg += "⚠️ **LOW STOCK ALERT:**\n" + "\n".join([f"- {i.name}: **{i.quantity} {i.unit}** (Min: {i.min_threshold})" for i in low])
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
                alert = " ⚠️ **LOW!**" if item.quantity <= item.min_threshold else ""
                return {"response": f"✅ Logged. **{item.name}**: {item.quantity} remaining.{alert}", "options": ["Log Another", "Stock Status"]}
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
# 2. REVENUE AGENT (With Real Treatments)
# =============================================================================
def handle_revenue_logic(db: Session, doctor_id: int, query: str):
    q_norm = query.lower().strip()
    now = datetime.now()
    
    # FETCH REAL TREATMENTS
    treatments = db.query(models.Treatment).filter(models.Treatment.doctor_id == doctor_id).all()
    # Create Rate Card Dict: { "Root Canal": 5000, ... }
    RC = {t.name: t.cost for t in treatments}
    if not RC: RC = {"Consultation": 500} # Fallback

    if q_norm in ["menu", "hi", "hello", "start", "main menu"]: return {"response": "Revenue Agent Active.", "options": ["Create New Invoice", "Show Unpaid Bills", "Daily Report", "Weekly Report"]}
    
    # Reports (Same as before)
    if q_norm == "daily report":
        s = now.replace(hour=0,minute=0)
        t = db.query(func.sum(models.Invoice.amount)).filter(models.Invoice.created_at>=s).scalar() or 0
        c = db.query(func.sum(models.Invoice.amount)).filter(models.Invoice.created_at>=s, models.Invoice.status=="paid", models.Invoice.details.like("%[Mode: Cash]%")).scalar() or 0
        o = db.query(func.sum(models.Invoice.amount)).filter(models.Invoice.created_at>=s, models.Invoice.status=="paid", models.Invoice.details.like("%[Mode: Online]%")).scalar() or 0
        return {"response": f"📊 **Today:**\n💰 Total: ₹{t}\n✅ Cash: ₹{c}\n💳 Online: ₹{o}\n⏳ Pending: ₹{t-(c+o)}", "options": ["Main Menu"]}

    # Create Invoice (Using Real Treatments)
    if q_norm == "create new invoice":
        appts = db.query(models.Appointment).filter(models.Appointment.doctor_id==doctor_id, models.Appointment.start_time>=now.replace(hour=0,minute=0)).all()
        return {"response": "Select patient or Type ID:", "options": [f"Bill: {a.patient.user.full_name} (ID:{a.patient_id})" for a in appts] + ["Main Menu"]}
    if q_norm.isdigit() or q_norm.startswith("id "):
        pid = int(re.sub(r"\D","",q_norm))
        p = db.query(models.Patient).filter(models.Patient.id==pid).first()
        return {"response": f"Billing **{p.user.full_name}**.", "options": [f"Add: {n} - ₹{v} | P:{pid}" for n,v in RC.items()]} if p else {"response": "ID Not Found", "options": ["Create New Invoice"]}
    if q_norm.startswith("bill:"):
        pid = re.search(r"\(id:(\d+)\)", q_norm).group(1)
        return {"response": "Select Procedure:", "options": [f"Add: {n} - ₹{p} | P:{pid}" for n, p in RC.items()]}
    
    # Add Invoice Logic (Same)
    if q_norm.startswith("add:"):
        p = q_norm.split(" | p:")
        n, v = p[0].replace("add: ", "").split(" - ₹")
        i = models.Invoice(patient_id=int(p[1]), amount=float(v), status="pending", created_at=now, details=n)
        db.add(i)
        db.commit()
        return {"response": f"✅ Bill Created: {n}", "options": [f"Cash | ID:{i.id}", f"Online | ID:{i.id}", "Later"]}
    
    # Pay Logic (Same)
    if q_norm == "show unpaid bills":
        u = db.query(models.Invoice).filter(models.Invoice.status=="pending").all()
        return {"response": "Unpaid Bills:", "options": [f"Pay: {i.patient.user.full_name} (₹{i.amount}) | ID:{i.id}" for i in u] + ["Main Menu"]}
    if q_norm.startswith("pay:"): return {"response": "Mode?", "options": [f"Cash | ID:{re.search(r'\| id:(\d+)', q_norm).group(1)}", f"Online | ID:{re.search(r'\| id:(\d+)', q_norm).group(1)}"]}
    if q_norm.startswith("cash") or q_norm.startswith("online"):
        i = db.query(models.Invoice).filter(models.Invoice.id==int(re.search(r"\| id:(\d+)", q_norm).group(1))).first()
        i.status="paid"; i.details+=f" [Mode: {'Cash' if 'cash' in q_norm else 'Online'}]"; db.commit()
        return {"response": "✅ Paid.", "options": ["Daily Report"]}
    if q_norm.startswith("void:"):
        db.query(models.Invoice).filter(models.Invoice.id==int(re.search(r"#(\d+)", q_norm).group(1))).delete(); db.commit()
        return {"response": "🗑️ Voided.", "options": ["Show Unpaid Bills"]}

    return {"response": "Unknown command.", "options": ["Main Menu"]}

# =============================================================================
# 3. APPOINTMENT AGENT (Using Real Treatments for Reasons)
# =============================================================================
def handle_appointment_logic(db: Session, doctor_id: int, query: str):
    auto_maintain_appointments(db, doctor_id)
    q_norm = query.lower().strip()
    now = datetime.now()
    
    # FETCH REAL REASONS
    treatments = db.query(models.Treatment).filter(models.Treatment.doctor_id == doctor_id).all()
    REASONS = [t.name for t in treatments] if treatments else ["Consultation"]

    if q_norm in ["menu", "hi", "hello", "start", "main menu"]: return {"response": "Hello, Doctor. Select an action:", "options": ["Show Today's Schedule", "Show This Week", "Show Previous Week", "Book Appointment", "Reschedule Appointment", "Cancel Appointment"]}
    if "schedule" in q_norm or "today" in q_norm or "week" in q_norm:
        if "previous week" in q_norm: start, end, title, stats = (now-timedelta(days=now.weekday()+7)).replace(hour=0,minute=0), (now-timedelta(days=now.weekday()+1)).replace(hour=23,minute=59), "Previous Week", ["completed", "cancelled", "confirmed"]
        elif "this week" in q_norm: start, end, title, stats = (now-timedelta(days=now.weekday())).replace(hour=0,minute=0), (now+timedelta(days=6)).replace(hour=23,minute=59), "This Week", ["confirmed", "pending", "checked-in", "in-progress", "completed"]
        else: start, end, title, stats = now.replace(hour=0,minute=0), now.replace(hour=23,minute=59), "Today", ["confirmed", "pending", "checked-in", "in-progress"]
        appts = db.query(models.Appointment).filter(models.Appointment.doctor_id==doctor_id, models.Appointment.start_time>=start, models.Appointment.start_time<=end, models.Appointment.status.in_(stats)).order_by(models.Appointment.start_time).all()
        msg = f"📅 **{title}:**\n" + ("\n".join([f"- {a.start_time.strftime('%I:%M %p')}: {a.patient.user.full_name} ({a.status.upper()} - {a.treatment_type or 'General'})" for a in appts]) if appts else "No records.")
        return {"response": msg, "options": ["Show Today", "Show This Week", "Show Previous Week", "Book Appointment", "Main Menu"]}
    
    # Booking Logic (Unchanged but uses dynamic REASONS now)
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
    if q_norm.startswith("select:"): return {"response": f"Pick date:", "options": [f"__UI_CALENDAR__|P:{re.search(r'\(id:\s*(\d+)\)', q_norm).group(1)}", "Main Menu"]}
    if q_norm.startswith("calendar_date:"):
        p = q_norm.replace("calendar_date: ", "").split("|")
        slots = get_smart_slots(db, doctor_id, p[0].strip())
        return {"response": f"Slots for **{p[0]}**:", "options": [f"Confirm: {p[0]} @ {t} | {p[1].strip()}" for t in slots]}
    if q_norm.startswith("confirm:"):
        p = q_norm.replace("confirm: ", "").split("| p:")
        if db.query(models.Appointment).filter(models.Appointment.patient_id==int(p[1]), models.Appointment.status.in_(["confirmed","pending"])).first(): return {"response": "Already has slot.", "options": ["Main Menu"]}
        # DYNAMIC REASONS HERE
        return {"response": "Select **Reason**:", "options": [f"Do: {r} | {q_norm.replace('confirm: ', '')}" for r in REASONS] + ["Do: Other | " + q_norm.replace('confirm: ', '')]}
    if q_norm.startswith("do:"):
        p = q_norm.replace("do: ", "").split(" | p:")
        reason, date_part = p[0].split(" | ")
        dt = datetime.strptime(date_part.strip().replace(" @ ", " "), "%Y-%m-%d %I:%M %p")
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
        db.flush() # Get ID
        
        # Look up cost
        trt = db.query(models.Treatment).filter(models.Treatment.name.ilike(reason), models.Treatment.doctor_id==doctor_id).first()
        cost = trt.cost if trt else 500.0 # Default if not found
        
        # Create Pending Invoice Immediately
        new_inv = models.Invoice(
            patient_id=int(p[1]),
            amount=cost,
            status="pending",
            created_at=datetime.utcnow(),
            details=f"Appointment: {reason}"
        )
        db.add(new_inv)
        db.commit()
        return {"response": f"✅ Booked for **{reason}**.", "options": ["Show Schedule"]}
    
    # Reschedule/Cancel/Checkout (Same as before but use REASONS/RC)
    if q_norm == "reschedule appointment":
        appts = db.query(models.Appointment).filter(models.Appointment.doctor_id==doctor_id, models.Appointment.start_time>now, models.Appointment.status.in_(["confirmed","pending"])).all()
        return {"response": "Reschedule whom?", "options": [f"Mod: {a.patient.user.full_name} | ID:{a.id}" for a in appts] + ["Main Menu"]}
    if q_norm.startswith("mod:"): return {"response": "Pick date:", "options": [f"__UI_CALENDAR__|ID:{re.search(r'\| id:(\d+)', q_norm).group(1)}", "Main Menu"]}
    if q_norm.startswith("reconfirm:"): return {"response": "Update Reason:", "options": [f"ReDo: {r} | {q_norm.replace('reconfirm: ', '')}" for r in REASONS] + ["ReDo: Same | " + q_norm.replace('reconfirm: ', '')]}
    if q_norm.startswith("redo:"):
        p = q_norm.replace("redo: ", "").split(" | id:")
        reason, date_part = p[0].split(" | ")
        dt = datetime.strptime(date_part.strip().replace(" @ ", " "), "%Y-%m-%d %I:%M %p")
        a = db.query(models.Appointment).filter(models.Appointment.id==int(p[1])).first()
        a.start_time=dt; a.end_time=dt+timedelta(minutes=30)
        if reason!="Same": a.treatment_type=reason
        db.commit()
        return {"response": "✅ Rescheduled.", "options": ["Show Schedule"]}
    if q_norm == "cancel appointment":
        appts = db.query(models.Appointment).filter(models.Appointment.doctor_id==doctor_id, models.Appointment.start_time>now, models.Appointment.status!="cancelled").all()
        return {"response": "Cancel whom?", "options": [f"Kill: {a.patient.user.full_name} - ID:{a.id}" for a in appts] + ["Main Menu"]}
    if q_norm.startswith("kill:"):
        aid=int(re.search(r"id:(\d+)", q_norm).group(1))
        a=db.query(models.Appointment).filter(models.Appointment.id==aid).first()
        a.status="cancelled"; db.query(models.Invoice).filter(models.Invoice.patient_id==a.patient_id, models.Invoice.status=="pending", func.date(models.Invoice.created_at)==a.start_time.date()).delete(synchronize_session=False); db.commit()
        return {"response": "✅ Cancelled.", "options": ["Show Schedule"]}
    if "manage" in q_norm and "id" in q_norm:
        aid = int(re.search(r"id\s*(\d+)", q_norm).group(1))
        st = db.query(models.Appointment).filter(models.Appointment.id==aid).first().status
        opts = [f"Start Appointment - ID {aid}", f"Cancel - ID {aid}"] if st=="checked-in" else [f"Start Appointment - ID {aid}", f"Mark Checked-In - ID {aid}", f"Cancel - ID {aid}"] if st=="confirmed" else [f"Complete & Bill - ID {aid}"]
        return {"response": f"Managing ID {aid}", "options": opts + ["Back"]}
    if "mark" in q_norm or "start appointment" in q_norm:
        st = "checked-in" if "checked-in" in q_norm else "in-progress"
        db.query(models.Appointment).filter(models.Appointment.id==int(re.search(r"id\s*(\d+)", q_norm).group(1))).update({"status": st})
        db.commit()
        return {"response": f"✅ Set to {st}", "options": ["Show Today's Schedule"]}
    
    # REVENUE CHECKOUT IN APPOINTMENT
    if "complete & bill" in q_norm:
        aid = int(re.search(r"id\s*(\d+)", q_norm).group(1))
        # Use RC from real treatments
        treatments = db.query(models.Treatment).filter(models.Treatment.doctor_id == doctor_id).all()
        RC = {t.name: t.cost for t in treatments}
        return {"response": "Select Procedure Done:", "options": [f"Done: {n} - ₹{p} | Appt:{aid}" for n, p in RC.items()]}
    
    if q_norm.startswith("done:"):
        p = q_norm.split(" | appt:")
        n, v = p[0].replace("done: ", "").split(" - ₹")
        a = db.query(models.Appointment).filter(models.Appointment.id==int(p[1])).first()
        a.status="completed"; # Find existing pending invoice for this patient/date
        i = db.query(models.Invoice).filter(
            models.Invoice.patient_id==a.patient_id, 
            models.Invoice.status=="pending",
            func.date(models.Invoice.created_at)==func.date(now)
        ).first()
        
        if not i:
            # Fallback if no invoice exists
            i = models.Invoice(patient_id=a.patient_id, amount=float(v), status="pending", created_at=now, details=n)
            db.add(i)
        db.commit()
        return {"response": f"✅ Completed. Mode?", "options": [f"Pay Cash | Inv:{i.id}", f"Pay Online | Inv:{i.id}", "Pay Later"]}
    if q_norm.startswith("pay cash") or q_norm.startswith("pay online"):
        i = db.query(models.Invoice).filter(models.Invoice.id==int(re.search(r"inv:(\d+)", q_norm).group(1))).first()
        i.status="paid"; i.details+=f" [Mode: {'Cash' if 'cash' in q_norm else 'Online'}]"; db.commit()
        return {"response": "🎉 Done.", "options": ["Show Today's Schedule"]}

    return {"response": "Error.", "options": ["Main Menu"]}

@router.post("/router")
async def route_agent(request: AgentRequest, user: models.User=Depends(get_current_user), db: Session=Depends(get_db)):
    try:
        agent = request.role.lower().replace(" ", "")
        doc = db.query(models.Doctor).filter(models.Doctor.user_id==user.id).first()
        if agent=="appointment": return handle_appointment_logic(db, doc.id, request.user_query)
        if agent=="revenue": return handle_revenue_logic(db, doc.id, request.user_query)
        if agent=="inventory": return handle_inventory_logic(db, doc.id, request.user_query)
        return {"response": "Ready.", "options": ["Main Menu"]}
    except Exception as e: return {"response": f"Error: {str(e)}", "options": ["Retry"]}




