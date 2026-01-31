# backend/notifications/email.py

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from datetime import datetime
import config

logger = logging.getLogger(__name__)

class EmailAdapter:
    """
    Real SMTP Email Adapter with SSL support (Port 465).
    """

    def send(self, to_email: str, subject: str, body: str, html_body: str = None):
        """
        Sends an email via SMTP_SSL.
        """
        try:
            # Create the container (outer) email message.
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{config.EMAIL_FROM_NAME} <{config.EMAIL_USER}>"
            msg['To'] = to_email

            # Record the MIME types of both parts - text/plain and text/html.
            part1 = MIMEText(body, 'plain')
            msg.attach(part1)

            # Attach HTML part if provided
            if html_body:
                part2 = MIMEText(html_body, 'html')
                msg.attach(part2)

            # --- KEY CHANGE: Use SMTP_SSL for Port 465 ---
            with smtplib.SMTP_SSL(config.EMAIL_HOST, config.EMAIL_PORT) as server:
                server.login(config.EMAIL_USER, config.EMAIL_PASSWORD)
                server.sendmail(config.EMAIL_USER, to_email, msg.as_string())
            
            logger.info(f"Email sent successfully to {to_email}")
            return {"status": "sent", "timestamp": datetime.utcnow().isoformat()}

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            # We re-raise the exception so main.py knows it failed
            raise e
