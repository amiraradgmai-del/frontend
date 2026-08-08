from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from email.utils import formataddr

from app.core.config import Settings

logger = logging.getLogger(__name__)


class EmailDeliveryError(RuntimeError):
    pass


class EmailSender:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def send_verification_code(self, email: str, first_name: str, code: str) -> None:
        if self.settings.email_delivery_mode == "console":
            logger.warning("Development verification code for %s: %s", email, code)
            return

        message = EmailMessage()
        message["Subject"] = "کد تأیید ایمیل شما"
        message["From"] = formataddr(
            (self.settings.smtp_from_name, self.settings.smtp_from_email or "")
        )
        message["To"] = email
        message.set_content(
            f"""سلام {first_name} عزیز،

به چکاه، دستیار هوشمند مالیاتی خوش آمدید.

کد تأیید ایمیل شما: {code}

این کد تا {self.settings.verification_code_minutes} دقیقه معتبر است. این کد را در اختیار هیچ‌کس قرار ندهید. تیم پشتیبانی هرگز کد تأیید یا رمز عبور شما را درخواست نمی‌کند.

اگر شما این درخواست را ثبت نکرده‌اید، این پیام را نادیده بگیرید.
"""
        )
        try:
            with smtplib.SMTP(
                self.settings.smtp_host, self.settings.smtp_port, timeout=15
            ) as smtp:
                if self.settings.smtp_use_tls:
                    smtp.starttls()
                smtp.login(self.settings.smtp_username, self.settings.smtp_password)
                smtp.send_message(message)
        except (OSError, smtplib.SMTPException) as error:
            raise EmailDeliveryError("Verification email could not be sent") from error

    def send_security_code(
        self, email: str, full_name: str, code: str, purpose: str
    ) -> None:
        if self.settings.email_delivery_mode == "console":
            logger.warning("Development security code for %s (%s): %s", email, purpose, code)
            return
        message = EmailMessage()
        message["Subject"] = f"کد تأیید {purpose}"
        message["From"] = formataddr(
            (self.settings.smtp_from_name, self.settings.smtp_from_email or "")
        )
        message["To"] = email
        message.set_content(
            f"""سلام {full_name} عزیز،

کد تأیید {purpose}: {code}

این کد دو دقیقه معتبر است. کد را در اختیار دیگران قرار ندهید.
اگر این درخواست را شما ثبت نکرده‌اید، با پشتیبانی چکاه تماس بگیرید.
"""
        )
        try:
            with smtplib.SMTP(
                self.settings.smtp_host, self.settings.smtp_port, timeout=15
            ) as smtp:
                if self.settings.smtp_use_tls:
                    smtp.starttls()
                smtp.login(self.settings.smtp_username, self.settings.smtp_password)
                smtp.send_message(message)
        except (OSError, smtplib.SMTPException) as error:
            raise EmailDeliveryError("Security code email could not be sent") from error

    def send_password_reset_code(self, email: str, full_name: str, code: str) -> None:
        self.send_security_code(email, full_name, code, "بازیابی رمز عبور")

    def send_notification(self, email: str, subject: str, message_text: str) -> None:
        if self.settings.email_delivery_mode == "console":
            logger.info("Email notification for %s: %s", email, subject)
            return
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = formataddr((self.settings.smtp_from_name, self.settings.smtp_from_email or ""))
        message["To"] = email
        message.set_content(message_text)
        try:
            with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=15) as smtp:
                if self.settings.smtp_use_tls:
                    smtp.starttls()
                smtp.login(self.settings.smtp_username, self.settings.smtp_password)
                smtp.send_message(message)
        except (OSError, smtplib.SMTPException) as error:
            raise EmailDeliveryError("Notification email could not be sent") from error
