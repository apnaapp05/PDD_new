import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from datetime import datetime
import config

logger = logging.getLogger(__name__)

class EmailAdapter:
    def send(self, to_email: str, subject: str, body: str, html_body: str = None):
        try:
            # 1. Setup Message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = config.EMAIL_USER
            msg['To'] = to_email

            # 2. Attach Content
            part1 = MIMEText(body, 'plain')
            msg.attach(part1)
            if html_body:
                part2 = MIMEText(html_body, 'html')
                msg.attach(part2)

            # 3. Connect to SMTP Server
            logger.info(f"Connecting to SMTP: {config.EMAIL_HOST}:{config.EMAIL_PORT}")
            
            # LOGIC FIX: Handle both Port 587 (TLS) and Port 465 (SSL)
            if config.EMAIL_PORT == 587:
                # Use standard SMTP with STARTTLS (The method that worked for you)
                with smtplib.SMTP(config.EMAIL_HOST, config.EMAIL_PORT) as server:
                    server.ehlo()
                    server.starttls()  # Upgrade connection to secure
                    server.ehlo()
                    server.login(config.EMAIL_USER, config.EMAIL_PASSWORD)
                    server.sendmail(config.EMAIL_USER, to_email, msg.as_string())
            else:
                # Use implicit SSL (Legacy/Port 465)
                with smtplib.SMTP_SSL(config.EMAIL_HOST, config.EMAIL_PORT) as server:
                    server.login(config.EMAIL_USER, config.EMAIL_PASSWORD)
                    server.sendmail(config.EMAIL_USER, to_email, msg.as_string())
            
            logger.info(f"✅ Email sent successfully to {to_email}")
            return {"status": "sent"}

        except Exception as e:
            logger.error(f"❌ Failed to send email: {e}")
            # Re-raise to ensure main.py knows it failed
            raise e