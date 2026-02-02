import pandas as pd
from sqlalchemy.orm import Session
from models import Appointment, Invoice, Treatment, Patient
from datetime import datetime, timedelta

class AnalystEngine:
    def __init__(self, db: Session, doctor_id: int):
        self.db = db
        self.doc_id = doctor_id

    def is_analysis_query(self, query: str) -> bool:
        keywords = ["analyze", "stats", "performance", "growth", "trend", "revenue", "how many", "busy", "pending"]
        q = query.lower()
        if "list" in q and "treatment" in q: return False # Let Brain handle lists
        return any(k in q for k in keywords)

    def analyze(self, query: str):
        q = query.lower()
        if any(x in q for x in ["revenue", "finance", "money", "pending", "outstanding", "payments"]):
            return self._analyze_financials(q)
        if any(x in q for x in ["schedule", "busy", "appointment", "volume"]):
            return self._analyze_schedule(q)
        if "patient" in q:
            return self._analyze_patients(q)
        return "I can analyze Financials, Schedule, or Patients."

    def _analyze_financials(self, query):
        invoices = self.db.query(Invoice).filter(Invoice.status != 'cancelled').all() # Add filtering in real app
        if not invoices: return "No financial records found."
        
        df = pd.DataFrame([{"amount": i.amount, "date": i.issue_date, "status": i.status} for i in invoices])
        
        # Pending Specific
        pending_total = df[df['status'] == 'pending']['amount'].sum()
        
        if "pending" in query or "outstanding" in query:
            count = len(df[df['status'] == 'pending'])
            return (
                f"💰 **Outstanding Collections**\n"
                f"- **Total Pending:** Rs. {pending_total:,.2f}\n"
                f"- **Unpaid Invoices:** {count}\n"
                f"- **Action:** You can ask me to 'Send payment reminders'."
            )

        # General Revenue
        total_rev = df['amount'].sum()
        return (
            f"💰 **Financial Overview**\n"
            f"- **Total Revenue:** Rs. {total_rev:,.2f}\n"
            f"- **Pending:** Rs. {pending_total:,.2f}\n"
        )

    def _analyze_schedule(self, query):
        appts = self.db.query(Appointment).filter(Appointment.doctor_id == self.doc_id).all()
        if not appts: return "Schedule is empty."
        df = pd.DataFrame([{"status": a.status} for a in appts])
        total = len(df)
        confirmed = len(df[df['status'].isin(['confirmed', 'completed'])])
        return f"📅 **Operations:** {total} total appointments ({confirmed} confirmed/completed)."

    def _analyze_patients(self, query):
        count = self.db.query(Patient).count()
        return f"👥 **Patient Base:** {count} active patients."
