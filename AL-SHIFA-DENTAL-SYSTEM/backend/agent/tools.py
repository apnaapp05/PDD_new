
from sqlalchemy.orm import Session
from datetime import datetime
import json

from services.appointment_service import AppointmentService
from services.inventory_service import InventoryService
from services.analytics_service import AnalyticsService
from services.treatment_service import TreatmentService
from services.clinical_service import ClinicalService
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
        self.treat_service = TreatmentService(db, doctor_id)
        self.clinical_service = ClinicalService(db, doctor_id)
        
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
        return json.dumps(schedule, default=str)

    def check_inventory_stock(self, item_name: str = None):
        """
        Check the stock level of a specific item or all low stock items.
        Args:
            item_name: The name of the item to check (optional). If None, checks for low stock items.
        """
        if item_name:
            # Simple linear search since we don't have get_by_name exposed yet or need to build it
            # For now, let's just get all and filter
            items = self.inv_service.get_all_items()
            for item in items:
                if item_name.lower() in item.name.lower():
                    return f"Found: {item.name}, Quantity: {item.quantity} {item.unit}, Min Threshold: {item.min_threshold}"
            return f"Item '{item_name}' not found in inventory."
        else:
            low_stock = self.inv_service.get_low_stock()
            if not low_stock: return "All stock levels are healthy."
            return json.dumps([{"name": i.name, "qty": i.quantity, "min": i.min_threshold} for i in low_stock])

    def get_revenue_report(self):
        """
        Get the revenue summary for the current month.
        """
        data = self.analytics_service.get_financial_summary()
        return f"Total Revenue: {data.get('revenue', 0)}, Pending Payments: {data.get('pending', 0)}"

    def book_appointment(self, patient_name: str, time: str, reason: str):
        """
        Book an appointment for a patient. 
        Args:
            patient_name: Name of the patient.
            time: Time of appointment (Try to provide format HH:MM if possible, or context).
            reason: Treatment type or reason for visit.
        """
        # Note: This is a simplified wrapper. Real booking might need patient ID lookup.
        # For the agent, we might need a distinct "find_patient" step or just return instructions.
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
        try:
            t = self.treat_service.create_treatment(name, cost)
            return f"Created treatment '{t.name}' with cost {t.cost}"
        except Exception as e:
            return f"Failed to create treatment: {str(e)}"

    def block_schedule(self, time: str, reason: str = "Blocked"):
        """
        Block a time slot in the schedule.
        Args:
            time: Start time to block (e.g. '14:00').
            reason: Reason for blocking.
        """
        return f"Please block {time} ({reason}) via the Calendar view to ensure no conflicts."

    def consult_knowledge_base(self, query: str):
        """
        Consult the clinical knowledge base (documents, protocols) to answer medical questions.
        Args:
            query: The clinical question or topic to search for (e.g. "root canal post op").
        """
        results = self.rag_store.search(query, n_results=3)
        
        if not results['documents'][0]:
            return "No relevant clinical protocols found."
            
        # Format the context
        context = ""
        for i, doc in enumerate(results['documents'][0]):
            source = results['metadatas'][0][i]['source']
            context += f"Source ({source}):\n{doc}\n\n"
            
        return f"Found the following protocols:\n{context}"


class PatientAgentTools:
    def __init__(self, db: Session, patient_id: int):
        self.db = db
        self.patient_id = patient_id
        # We pass None as doctor_id because the patient interacts with ANY doctor
        self.appt_service = AppointmentService(db, None) 

    def list_doctors(self):
        """Lists available doctors and their specializations."""
        docs = self.db.query(Doctor).all()
        return json.dumps([{
            "id": d.id, 
            "name": d.user.full_name, 
            "specialization": d.specialization,
            "hospital": d.hospital.name
        } for d in docs if d.user])

    def get_my_appointments(self):
         """Get confirmed upcoming appointments for this patient."""
         appts = self.appt_service.get_patient_upcoming(self.patient_id)
         if not appts: return "No upcoming appointments."
         return "\n".join([f"{a.start_time.strftime('%Y-%m-%d %I:%M %p')} with Dr. {a.doctor.user.full_name}" for a in appts])

    def cancel_appointment(self, appointment_id: int):
        """Cancel a specific appointment by ID."""
        try:
            # Need to get details BEFORE cancelling to send email
            appt_details = self.appt_service.get_appointment_by_id(appointment_id)
            
            self.appt_service.cancel_appointment_by_id(appointment_id, self.patient_id)
            
            # --- SEND EMAIL ---
            try:
                from notifications.email import EmailAdapter
                from models import Patient
                patient = self.db.query(Patient).filter(Patient.id == self.patient_id).first()
                
                if patient and patient.user.email and appt_details:
                     email_service = EmailAdapter()
                     subject = "Appointment Cancelled - Al-Shifa Dental"
                     body = f"Your appointment with Dr. {appt_details.doctor.user.full_name} on {appt_details.start_time} has been cancelled as requested."
                     email_service.send(patient.user.email, subject, body)
            except Exception as e:
                print(f"DEBUG: Email failed: {e}")
            # ------------------
            
            return "Appointment cancelled successfully. A confirmation email has been sent."
        except Exception as e:
            return f"Failed to cancel: {str(e)}"

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
                doctor_id=doctor_id,
                start_time=start_dt,
                reason=reason
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
            return f"❌ Booking failed: {str(e)}. Please check if the slot is free."

    def check_availability(self, doctor_id: int, date: str):
        """
        Get available time slots for a specific doctor and date.
        """
        try:
            # We need to temporarily set the doc_id in the service because PatientAgentTools service is init with None
            self.appt_service.doc_id = int(doctor_id) 
            slots = self.appt_service.get_available_slots(date)
            return json.dumps(slots)
        except Exception as e:
            return f"Error checking slots: {str(e)}"
