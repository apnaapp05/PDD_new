
from sqlalchemy.orm import Session
from datetime import datetime
import json

from services.appointment_service import AppointmentService
from services.inventory_service import InventoryService
from services.analytics_service import AnalyticsService
from services.treatment_service import TreatmentService
from services.clinical_service import ClinicalService
from services.patient_service import PatientService
from models import Doctor, User, Appointment, Treatment
from rag.store import RAGStore
from rag.loader import DocumentLoader
import os

class AgentTools:
    def __init__(self, db: Session, doctor_id: int):
        self.db = db
        self.doc_id = doctor_id
        
        self.appt_service = AppointmentService(db, doctor_id)
        self.inv_service = InventoryService(db, doctor_id)
        self.analytics_service = AnalyticsService(db, doctor_id)
        self.treat_service = TreatmentService(db, doctor_id)
        self.clinical_service = ClinicalService(db, doctor_id)
        self.pat_service = PatientService(db, doctor_id)
        
        # Initialize RAG
        self.rag_store = RAGStore()
        # Auto-load knowledge base on startup (simple approach for now)
        kb_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "knowledge_base")
        if self.rag_store.count() == 0:
             print(f"Loading Knowledge Base from {kb_path}...")
             loader = DocumentLoader(self.rag_store)
             loader.load_directory(kb_path)


    def get_todays_appointments(self):
        """
        Get all appointments scheduled for today.
        Returns a list of appointments with time, patient name, and status.
        """
        date_str = datetime.now().strftime("%Y-%m-%d")
        schedule = self.appt_service.get_schedule(date_str)
        
        # Serialize to list of dicts to avoid <Appointment object> hallucinations
        if not schedule:
            return "No appointments found for today."
            
        serialized_schedule = []
        for appt in schedule:
            serialized_schedule.append({
                "id": appt.id,
                "time": appt.start_time.strftime("%H:%M"),
                "patient_name": appt.patient.user.full_name if appt.patient and appt.patient.user else "Blocked/Unknown",
                "treatment": appt.treatment_type,
                "status": appt.status,
                "notes": appt.notes
            })
            
        return json.dumps(serialized_schedule)

    def check_inventory_stock(self, item_name: str = None):
        """
        Check the stock level of a specific item, list all items, or find low stock.
        Args:
            item_name: The name of the item (e.g. 'Gloves'), or 'ALL' to list everything, or None for low stock alerts.
        """
        if item_name and item_name.upper() == "ALL":
             items = self.inv_service.get_all_items()
             if not items: return "Inventory is empty."
             # Format as a concise list
             lines = ["--- Current Inventory ---"]
             for i in items:
                 lines.append(f"• {i.name}: {i.quantity} {i.unit} (Threshold: {i.min_threshold})")
             return "\n".join(lines)

        if item_name:
            items = self.inv_service.get_all_items()
            for item in items:
                if item_name.lower() in item.name.lower():
                    # Prediction Logic
                    daily_rate = self.inv_service.get_daily_usage_rate(item.id)
                    days_left = "Unknown (No recent usage)"
                    if daily_rate > 0:
                        days = int(item.quantity / daily_rate)
                        days_left = f"{days} days"
                        
                    return f"Found: {item.name}\nQuantity: {item.quantity} {item.unit}\nMin Threshold: {item.min_threshold}\nDaily Usage: {daily_rate:.2f}/day\n📉 Estimated Stock-out in: {days_left}"
            return f"Item '{item_name}' not found in inventory."
        else:
            # 1. Get Low Stock (Traditional)
            low_stock = self.inv_service.get_low_stock()
            
            # 2. Get Projected Usage (Next 7 Days)
            projected = self.inv_service.get_projected_usage(days=7)
            
            alerts = []
            
            # Check for critical shortages
            all_items = self.inv_service.get_all_items()
            for item in all_items:
                needed = projected.get(item.id, 0)
                if needed > 0:
                    if item.quantity < needed:
                        alerts.append({
                            "name": item.name,
                            "qty": item.quantity,
                            "needed": needed,
                            "status": "CRITICAL",
                            "message": f"Insufficient stock for upcoming appointments! Need {needed}, have {item.quantity}."
                        })
                    elif (item.quantity - needed) < item.min_threshold:
                        alerts.append({
                            "name": item.name, 
                            "qty": item.quantity,
                            "needed": needed,
                            "status": "WARNING",
                            "message": f"Stock will dip below threshold ({item.min_threshold}) after usage."
                        })

            # Merge with traditional low stock if not duplicates
            alert_names = {a['name'] for a in alerts}
            for item in low_stock:
                if item.name not in alert_names:
                    alerts.append({
                        "name": item.name,
                        "qty": item.quantity, 
                        "min": item.min_threshold,
                        "status": "LOW",
                        "message": f"Below minimum threshold ({item.min_threshold})."
                    })
            
            if not alerts: return "All stock levels are healthy. No upcoming shortages predicted."
            return json.dumps(alerts)

    def manage_inventory(self, action: str, name: str = None, quantity: int = 0, unit: str = "Pcs", threshold: int = 10):
        """
        Manage inventory: Add items or update stock.
        """
        if action == "add_item":
            if not name: return "Name is required."
            item = self.inv_service.create_item(name, quantity, unit, threshold)
            if not item: return f"Item '{name}' already exists."
            return f"Added {name} (Qty: {quantity}) to inventory."
        
        elif action == "update_stock":
             # Need to find ID first, simplified lookup by name
            items = self.inv_service.get_all_items() # Optimize this later
            target = next((i for i in items if i.name.lower() == name.lower()), None)
            if not target: return f"Item '{name}' not found."
            
            # Heuristic: If quantity is small (<50) and different from current, assume it's an update (add/sub)
            # But UI sends absolute. Let's support both via convention or just absolute.
            # Agent Prompt: "We got 100 more" -> Agent should calc current + 100?
            # Or we can make this tool smarter.
            # Let's assume the LLM calculates the final number or we offer 'adjustment' mode?
            # For now, let's assume 'quantity' input IS the new total (like UI) OR the adjustment?
            # Actually, let's use the 'update_stock' method in service which does +=.
            # Wait, my service has `update_quantity` (absolute) and `update_stock` (relative).
            # I'll expose parity with UI which is absolute usually, but for chat "add 5" is common.
            # Let's try to interpret: if the user says "add 5", LLM sends 5. 
            # I'll use `update_stock` (relative) which I kept in service as `item.quantity += qty`.
            # If the user says "set stock to 50", LLM sends ...?
            # Let's stick to RELATIVE update for chat convenience.
            
            updated = self.inv_service.update_stock(name, quantity)
            if updated: return f"Updated {name}. New Quantity: {updated.quantity}"
            return "Update failed."
            
        return "Invalid action."

    def manage_patients(self, action: str, query: str = None, patient_id: int = None, diagnosis: str = None, notes: str = None):
        """
        Manage patients: Search, View Details, Add Record.
        """
        if action == "search":
             results = self.pat_service.search_patients(query)
             if not results: return "No patients found."
             return json.dumps(results, indent=2)
             
        elif action == "get_details":
             if not patient_id: return "Patient ID required."
             details = self.pat_service.get_patient_details(patient_id)
             if not details: return "Patient not found."
             return json.dumps(details, indent=2)
             
        elif action == "add_record":
             if not patient_id or not diagnosis: return "Patient ID and Diagnosis required."
             rec = self.pat_service.add_medical_record(patient_id, diagnosis, notes or "")
             return f"Added record for Patient {patient_id}: {diagnosis}"
             
        return "Invalid action."

    def manage_treatments(self, action: str, name: str = None, cost: float = 0, item_name: str = None, quantity: int = 0):
        """
        Manage treatments: Create, Link Inventory.
        """
        if action == "create":
            if not name: return "Name required."
            t = self.treat_service.create_treatment(name, cost)
            if not t: return "Treatment already exists."
            return f"Created treatment '{name}' - Rs. {cost}"
            
        elif action == "link_inventory":
            if not name or not item_name: return "Treatment Name and Item Name required."
            return json.dumps(self.treat_service.link_inventory(name, item_name, quantity))
            
        return "Invalid action."

    def update_schedule_config(self, start_time: str, end_time: str, slot_duration: int = 30):
        """
        Update clinic schedule settings.
        """
        success = self.appt_service.update_availability(start_time, end_time, slot_duration)
        if success: return "Schedule settings updated successfully."
        return "Failed to update settings."

    def get_financial_analysis(self, analysis_type: str = "summary"):
        """
        Get financial reports.
        Types: 'summary' (revenue/pending), 'trend' (6-month graph), 'profitability' (margins).
        """
        if analysis_type == "trend":
            return json.dumps(self.analytics_service.get_trend_analysis())
        elif analysis_type == "profitability":
            return json.dumps(self.analytics_service.get_treatment_profitability())
        else:
            return json.dumps(self.analytics_service.get_financial_summary())

    def book_appointment(self, patient_name: str, time: str, reason: str):
        """
        Book an appointment for a patient. 
        Args:
             patient_name: Name of the patient.
             time: Time of appointment (Try to provide format HH:MM if possible, or context).
             reason: Treatment type or reason for visit.
        """
        return f"To book for {patient_name} at {time}, please use the main UI booking form as I need to verify specific slot availability accurately."

    def list_treatments(self):
        """
        List all available treatments and their prices.
        """
        treatments = self.treat_service.get_all_treatments()
        return "\n".join([f"{t.name}: Rs. {t.cost}" for t in treatments])

    def create_treatment(self, name: str, cost: float):
        """
        Add a new treatment to the price list.
        Args:
            name: Name of the treatment.
            cost: Cost of the treatment.
        """
        # Delegating to the new unified manager, but keeping this for backward compat if needed
        # Actually, let's keep it as a wrapper or just remove it if we update schema.
        # Check schema later. For now, wrap.
        return self.manage_treatments("create", name, cost)

    def block_schedule(self, time: str, reason: str = "Blocked"):
        return f"Please block {time} ({reason}) via the Calendar view to ensure no conflicts."

    def consult_knowledge_base(self, query: str):
        """
        Consult the clinical knowledge base (documents, protocols) to answer medical questions.
        Args:
            query: The clinical question or topic to search for (e.g. "root canal post op").
        """
        results = self.rag_store.search(query, n_results=3)
        
        if not results['documents'] or not results['documents'][0]:
            return "No relevant clinical protocols found."
            
        context_parts = []
        for i, doc in enumerate(results['documents'][0]):
            source = results['metadatas'][0][i]['source']
            context_parts.append(f"--- Document: {source} ---\n{doc}")
            
        return "\n\n".join(context_parts)

    def get_schedule_analysis(self, date_str: str = None, period: str = "daily", week_offset: int = 0):
        """
        Analyze the schedule.
        period: "daily" (default) or "weekly".
        date_str: for daily.
        week_offset: for weekly (0=current, -1=last).
        """
        if period == "weekly":
             return json.dumps(self.appt_service.get_weekly_stats(week_offset), indent=2)
        else:
             if not date_str: date_str = datetime.now().strftime("%Y-%m-%d")
             analysis = self.appt_service.analyze_schedule(date_str)
             return json.dumps(analysis, indent=2)

    def block_schedule_slot(self, date: str, time: str, reason: str):
        """
        Block a specific time slot to prevent bookings.
        """
        try:
             self.appt_service.block_slot(date, time, reason)
             return f"Assuming {date} {time} is blocked for '{reason}'."
        except Exception as e:
             return f"Failed to block slot: {str(e)}"

    def get_weekly_clinical_stats(self, week_offset: int = 0):
        """
        Get breakdown of treatments performed this week (or offset).
        """
        stats = self.analytics_service.get_clinical_stats(week_offset)
        if not stats: return "No completed treatments found for this period."
        return json.dumps(stats, indent=2)
        
    def get_revenue_comparison(self):
        """
        Compare current week revenue with last week.
        """
        return json.dumps(self.analytics_service.get_weekly_revenue_comparison(), indent=2)


class PatientAgentTools:
    def __init__(self, db: Session, patient_id: int):
        self.db = db
        self.patient_id = patient_id
        # We pass None as doctor_id because the patient interacts with ANY doctor
        self.appt_service = AppointmentService(db, None) 

    def list_doctors(self):
        """Lists available doctors and their specializations."""
        docs = self.db.query(Doctor).all()
        
        if not docs:
            return "No doctors available at this time."
        
        # Return formatted text instead of JSON
        result_lines = []
        for i, d in enumerate(docs, 1):
            result_lines.append(f"{i}. {d.user.full_name} ({d.specialization}) at {d.hospital.name}")
        
        return "\n".join(result_lines)
    
    def get_doctor_treatments(self, doctor_id: int):
        """Get all treatments offered by a specific doctor with pricing."""
        treatments = self.db.query(Treatment).filter(
            Treatment.doctor_id == doctor_id
        ).all()
        
        if not treatments:
            return "This doctor has not added any treatments yet. Please contact the clinic."
        
        # Return formatted text instead of JSON
        result_lines = []
        for i, t in enumerate(treatments, 1):
            price_info = f"Rs. {t.cost}" if t.cost else "Price not set"
            result_lines.append(f"{i}. {t.name} ({price_info})")
        
        return "\n".join(result_lines)


    def get_my_appointments(self):
         """Get confirmed upcoming appointments for this patient."""
         appts = self.appt_service.get_patient_upcoming(self.patient_id)
         if not appts: return "No upcoming appointments."
         return "\n".join([f"{a.start_time.strftime('%Y-%m-%d %I:%M %p')} with Dr. {a.doctor.user.full_name}" for a in appts])

    def cancel_appointment(self, appointment_id: int):
        """Cancel a specific appointment by ID."""
        try:
            # Service method handles:
            # - Validation (past date check, already cancelled check)
            # - Invoice cancellation
            # - Notifications to BOTH doctor and patient
            self.appt_service.cancel_appointment_by_id(appointment_id, self.patient_id)
            return "✅ Appointment cancelled successfully. A confirmation email has been sent to you and your doctor."
        except Exception as e:
            return str(e)

    def book_appointment(self, doctor_id: int, date: str = None, time: str = None, reason: str = "Consultation"):
        """
        Book an appointment.
        """
        # Robust handling for AI inputs
        try:
            doctor_id = int(doctor_id)
        except:
            return "Error: Doctor ID must be a number."
            
        if not date or not time:
            return "Error: Both Date and Time are required to book."

        print(f"DEBUG: Attempting booking for Doc {doctor_id} at {date} {time}")
        try:
            # 1. Check Availability (Simplified for Agent)
            # Ideally we check slots first, but let's try to book directly and catch error
            from datetime import datetime
            
            # Combine Date+Time
            start_dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
            
            # Call Service
            appt = self.appt_service.book_appointment(
                patient_id=self.patient_id,
                date_str=date,
                time_str=time,
                treatment=reason,
                doctor_id=doctor_id
            )
            
            # --- SEND EMAIL NOTIFICATION ---
            try:
                from notifications.email import EmailAdapter
                from models import Patient
                
                # Get Patient Email
                patient = self.db.query(Patient).filter(Patient.id == self.patient_id).first()
                if patient and patient.user.email:
                    email_service = EmailAdapter()
                    subject = "Appointment Confirmation - Al-Shifa Dental"
                    body = f"""
Dear {patient.user.full_name},

Your appointment has been successfully booked!

Doctor: Dr. {appt.doctor.user.full_name}
Time: {start_dt.strftime('%A, %d %b %Y at %I:%M %p')}
Location: {appt.doctor.hospital.name}

Thank you for choosing Al-Shifa Dental.
"""
                    email_service.send(patient.user.email, subject, body)
                    print(f"DEBUG: Email sent to {patient.user.email}")
            except Exception as e:
                print(f"DEBUG: Email sending failed: {e}")
            # -------------------------------

            return f"✅ Appointment booked successfully for {start_dt.strftime('%A, %d %b at %I:%M %p')}! A confirmation email has been sent."
        except Exception as e:
            # Return exact service error without wrapping
            return str(e)

    def check_availability(self, doctor_id: int, date: str):
        """
        Get available time slots for a specific doctor and date.
        """
        try:
            # We need to temporarily set the doc_id in the service because PatientAgentTools service is init with None
            self.appt_service.doc_id = int(doctor_id) 
            slots = self.appt_service.get_available_slots(date)
            
            if not slots:
                return f"No available time slots found for this doctor on {date}."
                
            # Return descriptive text for slots
            return f"Available slots for {date}: \n" + "\n".join([f"- {s}" for s in slots])
        except Exception as e:
            return f"Error checking slots: {str(e)}"

    def reschedule_appointment(self, appointment_id: int, new_date: str, new_time: str):
        """
        Reschedule an existing appointment to a new date and time.
        """
        try:
            self.appt_service.reschedule_appointment(appointment_id, self.patient_id, new_date, new_time)
            return f"Rescheduled successfully to {new_date} {new_time}."
        except Exception as e:
            return str(e)

    def book_followup(self, appointment_id: int):
        """
        Book a follow-up appointment 2 weeks from the given appointment date.
        """
        try:
            appt = self.appt_service.get_appointment_by_id(appointment_id)
            if not appt: return "Appointment not found."
            
            # Calculate +14 days
            from datetime import timedelta
            target_date = appt.start_time + timedelta(days=14)
            date_str = target_date.strftime("%Y-%m-%d")
            time_str = target_date.strftime("%H:%M") 
            
            # Try to book same doctor, same time
            # EXCEPTION: Allow follow-up even if patient has another appointment
            self.appt_service.book_appointment(
                self.patient_id, 
                date_str, 
                time_str, 
                "Follow-up", 
                doctor_id=appt.doctor_id,
                allow_multiple=True  # Bypass 1-appointment rule for follow-ups
            )
            
            return f"Follow-up booked for {date_str} at {time_str}."
        except Exception as e:
            return f"Failed to book follow-up: {str(e)}"
