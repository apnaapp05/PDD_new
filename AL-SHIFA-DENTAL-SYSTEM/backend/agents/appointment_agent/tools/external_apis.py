# dental-ai-system/appointment_agent/tools/external_apis.py
from typing import Optional, Dict, Any
from services_shared.db_client import APPOINTMENT_DB_CLIENT
from services_shared.message_bus.publisher import GLOBAL_PUBLISHER

class LiveAPITools:
    def search_availability(self, procedure_type: str, requested_datetime_range: str, doctor_name: Optional[str] = None) -> Dict[str, Any]:
        """Tool 1: Searches for availability (READ operation)."""
        sql = f"SELECT slot_id FROM clinic_schedule WHERE doctor='{doctor_name}' AND procedure='{procedure_type}'"
        db_result = APPOINTMENT_DB_CLIENT.execute_query(sql)
        return db_result

    def schedule_appointment(self, patient_id: str, slot_id: str, procedure_type: str) -> Dict[str, Any]:
        """Tool 2: Books a final appointment slot (WRITE operation)."""
        sql = f"UPDATE clinic_schedule SET patient_id='{patient_id}' WHERE slot_id='{slot_id}'"
        db_result = APPOINTMENT_DB_CLIENT.execute_query(sql)
        
        if db_result.get("status") == "success" and db_result["rows_affected"] > 0:
            return {"status": "success", "confirmation_id": f"CONF-DB-{slot_id}", "details": "Appointment confirmed."}
        return {"status": "error", "message": "Booking failed."}

    def send_reminder(self, patient_id: str, appointment_id: str, message_type: str):
        """Tool 3: Sends a proactive reminder (A2A Communication)."""
        message_payload = {
            "action": "SEND_REMINDER",
            "patient_id": patient_id,
            "appointment_id": appointment_id,
            "message_type": message_type,
            "source": "AppointmentAgent"
        }
        GLOBAL_PUBLISHER.publish_structured_message('clinic-reminders', message_payload)
        return {"status": "success", "message": "Reminder request queued."}

TOOL_MANAGER = LiveAPITools()