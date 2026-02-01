from datetime import datetime, timedelta
import re

class DateParser:
    @staticmethod
    def parse_datetime(text: str):
        """
        Converts natural language (today, tomorrow, 5pm) into 
        (YYYY-MM-DD, HH:MM) strings.
        """
        text = text.lower()
        now = datetime.now()
        target_date = now

        # 1. Parse Date
        if "today" in text:
            target_date = now
        elif "tomorrow" in text:
            target_date = now + timedelta(days=1)
        elif "next week" in text:
            target_date = now + timedelta(days=7)
        else:
            # Try to find YYYY-MM-DD or DD-MM-YYYY
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', text)
            if date_match:
                return date_match.group(1), None
        
        date_str = target_date.strftime("%Y-%m-%d")

        # 2. Parse Time
        time_str = None
        # Match "5pm", "5:30 pm", "17:00"
        time_match = re.search(r'(\d{1,2})(:(\d{2}))?\s*(am|pm)?', text)
        
        if time_match:
            # This is a basic parser logic
            hour = int(time_match.group(1))
            minute = time_match.group(3) or "00"
            period = time_match.group(4)

            if period == "pm" and hour < 12:
                hour += 12
            if period == "am" and hour == 12:
                hour = 0
            
            time_str = f"{hour:02}:{minute}"

        return date_str, time_str
