import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from app.core.config import settings


class EmailService:
    """Email service for sending password reset and other security-related emails."""
    
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "localhost")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.smtp_use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
        self.from_email = os.getenv("SMTP_FROM_EMAIL", "noreply@sportsinjuryrisk.com")
        self.development_mode = os.getenv("ENVIRONMENT", "development") == "development"
    
    def send_password_reset(self, to_email: str, reset_link: str, user_name: str) -> bool:
        """Send password reset email."""
        if self.development_mode:
            # In development, print the reset link instead of sending email
            print(f"\n[DEV MODE] Password Reset Link for {to_email}:")
            print(f"  {reset_link}\n")
            return True
        
        subject = "Password Reset Request - Sports Injury Risk Detection"
        body = f"""
Hello {user_name},

You have requested a password reset for your Sports Injury Risk Detection account.

Click the link below to reset your password:
{reset_link}

This link will expire in 1 hour.

If you did not request this password reset, please ignore this email and your password will remain unchanged.

For security reasons, please do not share this link with anyone.

Best regards,
Sports Injury Risk Detection Team
"""
        
        return self._send_email(to_email, subject, body)
    
    def send_otp(
        self, to_email: str, otp: str, purpose_label: str, expires_minutes: int
    ) -> bool:
        """Send a one-time password email.

        The raw code is only ever placed in the email body. In development it is
        printed to the console instead (clearly marked) and never sent.
        """
        if self.development_mode:
            # Development-only visibility for testing. Production
            # (ENVIRONMENT != "development") never prints codes.
            print(f"\n[DEV MODE] OTP for {to_email} ({purpose_label}): {otp} "
                  f"(expires in {expires_minutes} min)\n")
            return True

        subject = "Your verification code - Sports Injury Risk Detection"
        body = f"""
Hello,

You requested a verification code for {purpose_label}.

Your verification code is:

    {otp}

This code expires in {expires_minutes} minutes.

For your security:
  - Do not share this code with anyone.
  - Our team will never ask you for this code.
  - If you did not request it, you can safely ignore this email and your
    password will remain unchanged.

Best regards,
Sports Injury Risk Detection Team
"""
        return self._send_email(to_email, subject, body)

    def send_password_changed(self, to_email: str, user_name: str) -> bool:
        """Send password change confirmation email."""
        if self.development_mode:
            print(f"\n[DEV MODE] Password changed for {to_email}\n")
            return True
        
        subject = "Password Changed Successfully - Sports Injury Risk Detection"
        body = f"""
Hello {user_name},

Your password has been successfully changed.

If you did not make this change, please contact support immediately.

For your security, all existing sessions have been invalidated and you will need to log in again.

Best regards,
Sports Injury Risk Detection Team
"""
        
        return self._send_email(to_email, subject, body)
    
    def _send_email(self, to_email: str, subject: str, body: str) -> bool:
        """Internal method to send email via SMTP."""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.smtp_use_tls:
                    server.starttls()
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            return True
        except Exception as e:
            print(f"Failed to send email: {e}")
            return False


# Global email service instance
email_service = EmailService()
