from sqlalchemy.orm import Session
from models import Appointment, Patient, User, Invoice, Doctor
from datetime import datetime, timedelta
from notifications.service import NotificationService
from services.inventory_service import InventoryService

class AppointmentService:
    def __init__(self, db: Session, doctor_id: int):
        self.db = db
        self.doc_id = doctor_id
        self.notifier = NotificationService()

    def get_schedule(self, date_str: str = None, range_days: int = 0):
        query = self.db.query(Appointment).filter(Appointment.doctor_id == self.doc_id)
        if date_str:
            try:
                start_date = datetime.strptime(date_str, "%Y-%m-%d")
                end_date = start_date + timedelta(days=range_days + 1)
                query = query.filter(Appointment.start_time >= start_date, Appointment.start_time < end_date)
            except ValueError: pass
        return query.order_by(Appointment.start_time).all()

    # --- 1. BOOKING LOGIC (Preserved) ---
    def book_appointment(self, patient_id: int, date_str: str, time_str: str, treatment: str, doctor_id: int = None, allow_multiple: bool = False):
        """
        Book an appointment with strict 1-patient-1-appointment rule.
        
        Args:
            allow_multiple: Set to True to bypass the single appointment check (for reschedule/follow-up)
        """
        target_doc_id = doctor_id if doctor_id else self.doc_id
        if not target_doc_id: raise ValueError("Doctor ID required for booking.")
        
        try:
            start_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            end_dt = start_dt + timedelta(minutes=30)
            
            # VALIDATION 1: Cannot book in the past
            if start_dt <= datetime.now():
                raise ValueError("Cannot book appointments in the past. Please select a future date and time.")
            
            # VALIDATION 2: Maximum advance booking (90 days)
            max_advance_days = 90
            if start_dt > datetime.now() + timedelta(days=max_advance_days):
                raise ValueError(f"Cannot book more than {max_advance_days} days in advance. Please select a closer date.")
            
            # VALIDATION 3: Business hours check
            doctor = self.db.query(Doctor).filter(Doctor.id == target_doc_id).first()
            if doctor and doctor.scheduling_config:
                try:
                    import json
                    config = json.loads(doctor.scheduling_config)
                    work_start = config.get("work_start_time", "09:00")
                    work_end = config.get("work_end_time", "17:00")
                    
                    # Parse work hours
                    work_start_hour, work_start_min = map(int, work_start.split(":"))
                    work_end_hour, work_end_min = map(int, work_end.split(":"))
                    
                    booking_time = start_dt.time()
                    work_start_time = datetime.strptime(work_start, "%H:%M").time()
                    work_end_time = datetime.strptime(work_end, "%H:%M").time()
                    
                    if booking_time < work_start_time or booking_time >= work_end_time:
                        raise ValueError(
                            f"Booking time must be within doctor's working hours "
                            f"({work_start} - {work_end}). Please select a time during clinic hours."
                        )
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    # If config parsing fails, use default 9 AM - 5 PM
                    booking_hour = start_dt.hour
                    if booking_hour < 9 or booking_hour >= 17:
                        raise ValueError("Booking time must be between 9 AM and 5 PM.")
            
            # VALIDATION 4: Check if patient already has a future appointment
            if not allow_multiple:
                existing = self.db.query(Appointment).filter(
                    Appointment.patient_id == patient_id,
                    Appointment.start_time > datetime.now(),
                    Appointment.status.in_(['confirmed', 'pending'])
                ).first()
                
                if existing:
                    existing_date = existing.start_time.strftime("%d %b %Y at %I:%M %p")
                    raise ValueError(
                        f"You already have an appointment on {existing_date}. "
                        f"Please cancel or reschedule it first."
                    )
            
            # VALIDATION 5: Check for overlaps (doctor's schedule including blocked slots)
            self._check_overlap(start_dt, end_dt, target_doc_id)

            # VALIDATION 6: Check if treatment is offered by doctor
            from models import Treatment
            treatment_obj = self.db.query(Treatment).filter(
                Treatment.doctor_id == target_doc_id,
                Treatment.name.ilike(treatment)
            ).first()
            
            if not treatment_obj:
                raise ValueError(
                    f"Treatment '{treatment}' is not offered by this doctor. "
                    f"Please contact the clinic for available treatments."
                )
            
            # Create Appointment
            appt = Appointment(
                doctor_id=target_doc_id,
                patient_id=patient_id,
                start_time=start_dt,
                end_time=end_dt,
                status="confirmed",
                treatment_type=treatment,
                notes="AI Booking"
            )
            self.db.add(appt)
            self.db.flush() 

            self.db.commit()
            self.db.refresh(appt)
            
            # --- PROACTIVE INVENTORY CHECK ---
            try:
                # Run the check asynchronously or safely so it doesn't block/fail the booking
                inv_service = InventoryService(self.db, target_doc_id)
                inv_service.check_stock_health_for_new_booking(treatment)
            except Exception as e:
                print(f"Inventory Forecast Check Failed: {e}")
            # ---------------------------------

            return appt
            
        except ValueError as e:
            self.db.rollback()
            raise e

    # --- 2. CANCEL LOGIC (New) ---
    def get_appointment_by_id(self, appointment_id: int):
        return self.db.query(Appointment).filter(Appointment.id == appointment_id).first()

    def get_patient_upcoming(self, patient_id: int):
        """Fetch confirmed/pending appointments in the future"""
        return self.db.query(Appointment).filter(
            Appointment.patient_id == patient_id,
            Appointment.start_time > datetime.now(),
            Appointment.status.in_(["confirmed", "pending"])
        ).order_by(Appointment.start_time).all()
    
    # --- AUTO-CANCELLATION FOR NO-SHOWS ---
    def auto_cancel_no_shows(self):
        """
        Auto-cancel appointments from previous days that were never started.
        Run this at midnight daily via scheduler.
        
        Business Rule:
        - If appointment time has passed and status is still 'confirmed' or 'pending'
        - Auto-mark as 'cancelled' 
        - Cancel associated invoice
        - Log for doctor review
        """
        from datetime import date
        
        today_start = datetime.combine(date.today(), datetime.min.time())
        
        # Find all past appointments still in pending/confirmed state
        stale_appointments = self.db.query(Appointment).filter(
            Appointment.end_time < today_start,  # Before today
            Appointment.status.in_(['confirmed', 'pending'])
        ).all()
        
        cancelled_count = 0
        for appt in stale_appointments:
            # Mark as cancelled
            appt.status = 'cancelled'
            
            # Cancel invoice
            invoice = self.db.query(Invoice).filter(
                Invoice.appointment_id == appt.id,
                Invoice.status == 'pending'
            ).first()
            
            if invoice:
                invoice.status = 'cancelled'
            
            cancelled_count += 1
        
        if cancelled_count > 0:
            self.db.commit()
            print(f"✅ Auto-cancelled {cancelled_count} no-show appointments")
        
        return cancelled_count


    def cancel_appointment_by_id(self, appointment_id: int, patient_id: int):
        """
        Cancel an appointment with proper validation and notifications.
        
        Business Rules:
        - Can only cancel future appointments (not past/completed)
        - Auto-cancels associated invoice
        - Notifies both doctor and patient
        """
        appt = self.db.query(Appointment).filter(
            Appointment.id == appointment_id,
            Appointment.patient_id == patient_id
        ).first()
        
        if not appt:
            raise ValueError("Appointment not found or access denied.")
        
        # VALIDATION: Only cancel future appointments
        if appt.start_time <= datetime.now():
            raise ValueError("Cannot cancel past or ongoing appointments. Please contact the clinic directly.")
        
        # VALIDATION: Don't cancel already cancelled appointments
        if appt.status == "cancelled":
            raise ValueError("This appointment is already cancelled.")
        
        # Update appointment status
        appt.status = "cancelled"
        
        # Auto-cancel invoice
        invoice = self.db.query(Invoice).filter(
            Invoice.appointment_id == appointment_id,
            Invoice.status == "pending"
        ).first()
        
        if invoice:
            invoice.status = "cancelled"
        
        self.db.commit()
        
        # Send notifications to both doctor and patient
        try:
            patient = self.db.query(Patient).filter(Patient.id == patient_id).first()
            doctor = self.db.query(Doctor).filter(Doctor.id == appt.doctor_id).first()
            
            if patient and doctor:
                # Notify patient
                self.notifier.send_cancellation_email(
                    patient_email=patient.user.email,
                    patient_name=patient.user.full_name,
                    doctor_name=doctor.user.full_name,
                    appointment_date=appt.start_time.strftime("%d %b %Y"),
                    appointment_time=appt.start_time.strftime("%I:%M %p")
                )
                
                # Notify doctor
                self.notifier.send_doctor_cancellation_notification(
                    doctor_email=doctor.user.email,
                    doctor_name=doctor.user.full_name,
                    patient_name=patient.user.full_name,
                    appointment_date=appt.start_time.strftime("%d %b %Y"),
                    appointment_time=appt.start_time.strftime("%I:%M %p")
                )
        except Exception as e:
            print(f"Notification error: {e}")
            # Don't fail cancellation if notification fails
        
        return appt

    # --- 3. RESCHEDULE LOGIC (New) ---
    def reschedule_appointment(self, appointment_id: int, patient_id: int, new_date: str, new_time: str):
        """
        Updates the time of an existing appointment.
        Notifies both doctor and patient of the change.
        """
        appt = self.db.query(Appointment).filter(
            Appointment.id == appointment_id,
            Appointment.patient_id == patient_id
        ).first()
        
        if not appt:
            raise ValueError("Appointment not found.")

        try:
            # Store old time for notification
            old_date = appt.start_time.strftime("%d %b %Y")
            old_time = appt.start_time.strftime("%I:%M %p")
            
            start_dt = datetime.strptime(f"{new_date} {new_time}", "%Y-%m-%d %H:%M")
            end_dt = start_dt + timedelta(minutes=30)
            
            # VALIDATION 1: Cannot reschedule to the past
            if start_dt <= datetime.now():
                raise ValueError("Cannot reschedule to a past date/time. Please select a future slot.")
            
            # VALIDATION 2: Maximum advance booking (90 days)
            max_advance_days = 90
            if start_dt > datetime.now() + timedelta(days=max_advance_days):
                raise ValueError(f"Cannot reschedule more than {max_advance_days} days in advance.")
            
            # VALIDATION 3: Business hours check
            doctor = self.db.query(Doctor).filter(Doctor.id == appt.doctor_id).first()
            if doctor and doctor.scheduling_config:
                try:
                    import json
                    config = json.loads(doctor.scheduling_config)
                    work_start = config.get("work_start_time", "09:00")
                    work_end = config.get("work_end_time", "17:00")
                    
                    booking_time = start_dt.time()
                    work_start_time = datetime.strptime(work_start, "%H:%M").time()
                    work_end_time = datetime.strptime(work_end, "%H:%M").time()
                    
                    if booking_time < work_start_time or booking_time >= work_end_time:
                        raise ValueError(
                            f"Time must be within doctor's working hours ({work_start} - {work_end})."
                        )
                except (json.JSONDecodeError, KeyError, ValueError):
                    booking_hour = start_dt.hour
                    if booking_hour < 9 or booking_hour >= 17:
                        raise ValueError("Booking time must be between 9 AM and 5 PM.")
            
            # VALIDATION 4: Check availability (excluding current appointment ID to allow minor shifts)
            overlap = self.db.query(Appointment).filter(
                Appointment.doctor_id == appt.doctor_id,
                Appointment.start_time < end_dt,
                Appointment.end_time > start_dt,
                Appointment.status != 'cancelled',
                Appointment.id != appointment_id 
            ).first()
            
            if overlap:
                raise ValueError("The new slot is already taken.")
            
            # Update appointment times
            appt.start_time = start_dt
            appt.end_time = end_dt
            self.db.commit()
            
            # Send notifications to both doctor and patient
            try:
                patient = self.db.query(Patient).filter(Patient.id == patient_id).first()
                
                if patient and doctor:
                    new_date_str = start_dt.strftime("%d %b %Y")
                    new_time_str = start_dt.strftime("%I:%M %p")
                    
                    # Notify patient
                    self.notifier.send_reschedule_email(
                        patient_email=patient.user.email,
                        patient_name=patient.user.full_name,
                        doctor_name=doctor.user.full_name,
                        old_date=old_date,
                        old_time=old_time,
                        new_date=new_date_str,
                        new_time=new_time_str
                    )
                    
                    # Notify doctor
                    self.notifier.send_doctor_reschedule_notification(
                        doctor_email=doctor.user.email,
                        doctor_name=doctor.user.full_name,
                        patient_name=patient.user.full_name,
                        old_date=old_date,
                        old_time=old_time,
                        new_date=new_date_str,
                        new_time=new_time_str
                    )
            except Exception as e:
                print(f"Notification error: {e}")
                # Don't fail reschedule if notification fails
            
            return appt
            
        except ValueError as e:
            raise e

    # --- HELPER ---
    def _check_overlap(self, start_dt, end_dt, doctor_id=None):
        target_doc_id = doctor_id if doctor_id else self.doc_id
        overlap = self.db.query(Appointment).filter(
            Appointment.doctor_id == target_doc_id,
            Appointment.start_time < end_dt,
            Appointment.end_time > start_dt,
            Appointment.status != 'cancelled'
        ).first()
        if overlap: raise ValueError(f"Slot is already occupied.")

    # Legacy/Doctor block
    def block_slot(self, date_str: str, time_str: str, reason: str):
        # Implementation for doctor blocking (simplified here)
        return self.book_appointment(None, date_str, time_str, "Blocked") 

    def get_available_slots(self, date_str: str):
        """
        Generate available 30-minute slots for a given date (09:00 - 17:00).
        """
        booked = self.get_schedule(date_str)
        booked_times = {a.start_time.strftime("%H:%M") for a in booked if a.status != 'cancelled'}
        
        slots = []
        start_hour = 9  # 9 AM
        end_hour = 17   # 5 PM
        
        current_dt = datetime.strptime(f"{date_str} {start_hour}:00", "%Y-%m-%d %H:%M")
        end_dt_limit = datetime.strptime(f"{date_str} {end_hour}:00", "%Y-%m-%d %H:%M")
        
        while current_dt < end_dt_limit:
            time_str = current_dt.strftime("%H:%M")
            if time_str not in booked_times:
                # Extra check: Don't show past slots for TODAY
                if current_dt > datetime.now():
                    slots.append(time_str)
            current_dt += timedelta(minutes=30)
            
        return slots 

    def analyze_schedule(self, date_str: str):
        """
        Analyze the schedule to give a summary for the Agent.
        """
        appts = self.get_schedule(date_str)
        total_slots = 16 # 8 hours * 2 slots/hr (9-5)
        booked_count = len([a for a in appts if a.status != 'cancelled'])
        
        # Calculate free time ranges
        # Simple implementation: rely on get_available_slots
        free_slots = self.get_available_slots(date_str)
        
        # Categorize
        notes = []
        if booked_count == 0: notes.append("Completely free day.")
        elif booked_count > 12: notes.append("Very busy day.")
        
        # Treatment Breakdown
        breakdown = {}
        for a in appts:
            if a.status == 'cancelled': continue
            t = a.treatment_type or "General"
            breakdown[t] = breakdown.get(t, 0) + 1
            
        return {
            "date": date_str,
            "total_patients": booked_count,
            "occupancy": f"{int((booked_count/total_slots)*100)}%",
            "free_slots_count": len(free_slots),
            "free_slots_examples": free_slots[:3], # Just show first 3
            "treatments": breakdown,
            "notes": notes
        } 

    def get_weekly_stats(self, week_offset: int = 0):
        """
        Analyze schedule for a full week.
        week_offset: 0 = This Week, 1 = Next Week, -1 = Last Week
        """
        from datetime import date, timedelta
        
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday()) # Monday
        
        # Apply offset
        target_monday = start_of_week + timedelta(weeks=week_offset)
        target_sunday = target_monday + timedelta(days=6)
        
        # Fetch all appointments in range
        appts = self.db.query(Appointment).filter(
            Appointment.doctor_id == self.doc_id,
            Appointment.start_time >= datetime.combine(target_monday, datetime.min.time()),
            Appointment.end_time <= datetime.combine(target_sunday, datetime.max.time()),
            Appointment.status != 'cancelled'
        ).all()
        
        # Aggregate
        daily_stats = {}
        total_slots_per_day = 16
        
        # Initialize days
        for i in range(7):
            d = target_monday + timedelta(days=i)
            day_name = d.strftime("%A")
            daily_stats[day_name] = {"count": 0, "occupancy": 0}
            
        for a in appts:
            day_name = a.start_time.strftime("%A")
            if day_name in daily_stats:
                daily_stats[day_name]["count"] += 1
                
        # Calculate Occupancy
        busy_days = []
        for day, stats in daily_stats.items():
            occ = int((stats["count"] / total_slots_per_day) * 100)
            stats["occupancy"] = f"{occ}%"
            if occ > 70: busy_days.append(day)
            
        return {
            "period": f"{target_monday} to {target_sunday}",
            "total_appointments": len(appts),
            "daily_breakdown": daily_stats,
            "busy_days": busy_days,
            "summary": "High volume week." if len(appts) > 40 else "Moderate schedule." if len(appts) > 15 else "Light schedule."
        }

    def update_availability(self, start_time: str, end_time: str, slot_duration: int = 30):
        """
        Update doctor's work hours and slot settings.
        """
        import json
        doc = self.db.query(Doctor).filter(Doctor.id == self.doc_id).first()
        if not doc: return False
        
        config = {
            "work_start_time": start_time,
            "work_end_time": end_time,
            "slot_duration": slot_duration,
            "break_duration": 5 # Default
        }
        
        doc.scheduling_config = json.dumps(config)
        self.db.commit()
        return True
