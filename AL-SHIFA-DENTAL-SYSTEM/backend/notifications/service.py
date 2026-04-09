from notifications.whatsapp import WhatsAppAdapter
from notifications.email import EmailAdapter
from infra.retry_queue import RetryQueue
from infra.monitoring import MonitoringLogger


class NotificationService:
    """
    Resilient Notification Service
    - Retry on failure
    - Audited
    """

    def __init__(self):
        self.whatsapp = WhatsAppAdapter()
        self.email = EmailAdapter()
        self.retry_queue = RetryQueue()

    def notify_whatsapp(self, to_number: str, message: str):
        MonitoringLogger.log(
            agent="notification",
            action="whatsapp_send_attempt",
            payload={"to": to_number}
        )

        return self.retry_queue.execute(
            self.whatsapp.send,
            {
                "to_number": to_number,
                "message": message
            }
        )

    def notify_email(self, to_email: str, subject: str, body: str):
        MonitoringLogger.log(
            agent="notification",
            action="email_send_attempt",
            payload={"to": to_email, "subject": subject}
        )

        return self.retry_queue.execute(
            self.email.send,
            {
                "to_email": to_email,
                "subject": subject,
                "body": body
            }
        )
    
    # --- Appointment-Specific Notifications ---
    
    def send_cancellation_email(self, patient_email: str, patient_name: str, doctor_name: str, appointment_date: str, appointment_time: str):
        """Send cancellation confirmation to patient"""
        subject = "Appointment Cancelled - Al-Shifa Dental Clinic"
        body = f"""
Dear {patient_name},

Your appointment has been successfully cancelled.

Appointment Details:
- Doctor: Dr. {doctor_name}
- Date: {appointment_date}
- Time: {appointment_time}

If you wish to book a new appointment, please log in to your patient portal.

Best regards,
Al-Shifa Dental Clinic
        """
        return self.notify_email(patient_email, subject, body.strip())
    
    def send_doctor_cancellation_notification(self, doctor_email: str, doctor_name: str, patient_name: str, appointment_date: str, appointment_time: str):
        """Notify doctor about patient cancellation"""
        subject = f"Appointment Cancelled by Patient - {appointment_date}"
        body = f"""
Dear Dr. {doctor_name},

A patient has cancelled their appointment.

Cancelled Appointment:
- Patient: {patient_name}
- Date: {appointment_date}
- Time: {appointment_time}

The slot is now available for other bookings.

Best regards,
Al-Shifa Dental System
        """
        return self.notify_email(doctor_email, subject, body.strip())
    
    def send_reschedule_email(self, patient_email: str, patient_name: str, doctor_name: str, old_date: str, old_time: str, new_date: str, new_time: str):
        """Send reschedule confirmation to patient"""
        subject = "Appointment Rescheduled - Al-Shifa Dental Clinic"
        body = f"""
Dear {patient_name},

Your appointment has been successfully rescheduled.

Previous Appointment:
- Date: {old_date}
- Time: {old_time}

New Appointment:
- Doctor: Dr. {doctor_name}
- Date: {new_date}
- Time: {new_time}

Please arrive 10 minutes early for registration.

Best regards,
Al-Shifa Dental Clinic
        """
        return self.notify_email(patient_email, subject, body.strip())
    
    def send_doctor_reschedule_notification(self, doctor_email: str, doctor_name: str, patient_name: str, old_date: str, old_time: str, new_date: str, new_time: str):
        """Notify doctor about appointment reschedule"""
        subject = f"Appointment Rescheduled - {patient_name}"
        body = f"""
Dear Dr. {doctor_name},

An appointment has been rescheduled.

Patient: {patient_name}

Previous Time:
- {old_date} at {old_time}

New Time:
- {new_date} at {new_time}

Please update your schedule accordingly.

Best regards,
Al-Shifa Dental System
        """
        return self.notify_email(doctor_email, subject, body.strip())

    def send_low_stock_notification(self, doctor_email: str, doctor_name: str, item_name: str, current_quantity: int, min_threshold: int):
        """Notify doctor about low inventory stock"""
        subject = f"🚨 Low Stock Alert: {item_name}"
        body = f"""
Dear Dr. {doctor_name},

This is an automated alert to inform you that an inventory item is running low.

Item Details:
- Name: {item_name}
- Current Quantity: {current_quantity}
- Minimum Level: {min_threshold}

Please restock this item soon to ensure uninterrupted operations.

Best regards,
Al-Shifa Dental System
        """
        return self.notify_email(doctor_email, subject, body.strip())
