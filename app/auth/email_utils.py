import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import get_settings
import logging

settings = get_settings()
logger = logging.getLogger(__name__)


class EmailService:
    """Email sending service using SMTP."""

    @staticmethod
    def send_password_reset_email(to_email: str, token: str) -> bool:
        """Send password reset email."""
        try:
            subject = "CareerLens - Reset Your Password"

            # ✅ Use backend URL from settings
            reset_link = (
                f"{settings.BACKEND_BASE_URL}/auth/reset-password?token={token}"
            )

            body = f"""
            <html>
                <body style="font-family: Arial, sans-serif; padding: 20px;">
                    <h2>Reset Your Password</h2>
                    <p>Click the link below to reset your password:</p>
                    <p>
                        <a href="{reset_link}" 
                           style="background-color: #4CAF50; color: white; padding: 10px 20px; 
                                  text-decoration: none; border-radius: 5px; display: inline-block;">
                            Reset Password
                        </a>
                    </p>
                    <p>This link will expire in 24 hours.</p>
                    <p>Best regards,<br>CareerLens Team</p>
                </body>
            </html>
            """

            EmailService._send_smtp_email(to_email, subject, body)
            logger.info(f"Password reset email sent to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send password reset email: {str(e)}")
            return False

    @staticmethod
    def _send_smtp_email(to_email: str, subject: str, body: str) -> None:
        """Send email via SMTP."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.FROM_EMAIL
        msg["To"] = to_email

        part = MIMEText(body, "html")
        msg.attach(part)

        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.FROM_EMAIL, [to_email], msg.as_string())
