from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from models import Invoice, Appointment, Patient, User
import pandas as pd
from datetime import datetime, timedelta

class AnalyticsService:
    def __init__(self, db: Session, doctor_id: int):
        self.db = db
        self.doc_id = doctor_id

    def get_financial_summary(self, period="all"):
        """
        Returns:
        1. Stats (Revenue, Pending)
        2. Recent Invoices List (for the table)
        """
        # Base Query
        query = self.db.query(Invoice).join(Appointment).filter(
            Appointment.doctor_id == self.doc_id
        )
        
        # Period Filter
        now = datetime.now()
        if period == "today":
            query = query.filter(Invoice.created_at >= now.replace(hour=0, minute=0))
        elif period == "week":
            query = query.filter(Invoice.created_at >= now - timedelta(days=7))
            
        invoices = query.order_by(desc(Invoice.created_at)).all()
        
        # 1. Calculate Stats
        total_revenue = 0
        pending = 0
        if invoices:
            df = pd.DataFrame([{"amount": i.amount, "status": i.status} for i in invoices])
            total_revenue = df[df["status"] == "paid"]["amount"].sum()
            pending = df[df["status"] == "pending"]["amount"].sum()

        # 2. Format List for Table
        invoice_list = []
        for inv in invoices:
            # Safe Patient Name Lookup
            patient_name = "Unknown"
            if inv.patient and inv.patient.user:
                patient_name = inv.patient.user.full_name
            elif inv.appointment and inv.appointment.patient and inv.appointment.patient.user:
                patient_name = inv.appointment.patient.user.full_name

            invoice_list.append({
                "id": inv.id,
                "patient_name": patient_name,
                "procedure": inv.appointment.treatment_type if inv.appointment else "Consultation",
                "amount": inv.amount,
                "status": inv.status,
                "date": inv.created_at.strftime("%Y-%m-%d"),
                "time": inv.created_at.strftime("%H:%M")
            })

        return {
            "revenue": total_revenue,
            "pending": pending,
            "count": len(invoices),
            "invoices": invoice_list # <--- The Missing Link
        }

    def get_treatment_popularity(self):
        results = self.db.query(
            Appointment.treatment_type, func.count(Appointment.id)
        ).filter(
            Appointment.doctor_id == self.doc_id
        ).group_by(Appointment.treatment_type).all()
        return sorted(results, key=lambda x: x[1], reverse=True)
