from sqlalchemy.orm import Session
from models import Invoice, Appointment
import pandas as pd
from sqlalchemy import func

class FinanceTools:
    def __init__(self, db: Session, doctor_id: int):
        self.db = db
        self.doc_id = doctor_id

    def analyze_revenue(self):
        """Uses Pandas to analyze financial health."""
        invoices = self.db.query(Invoice).join(Appointment).filter(
            Appointment.doctor_id == self.doc_id
        ).all()
        
        if not invoices: return "No financial data available."

        data = [{"Amount": i.amount, "Status": i.status, "Date": i.created_at} for i in invoices]
        df = pd.DataFrame(data)
        
        total_rev = df[df["Status"] == "paid"]["Amount"].sum()
        pending = df[df["Status"] == "pending"]["Amount"].sum()
        
        return f"💰 Financial Snapshot:\n- Total Collected: Rs. {total_rev}\n- Pending Dues: Rs. {pending}\n- Total Invoices: {len(df)}"
