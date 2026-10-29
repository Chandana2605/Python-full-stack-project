import asyncio
import smtplib
import ssl
from email.message import EmailMessage

from ..core.config import get_settings
from ..exceptions.http_exceptions import bad_request_exception


class EmailService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def send_user_invitation(
        self,
        *,
        recipient_name: str,
        recipient_email: str,
        temporary_password: str,
        role_label: str,
    ) -> dict:
        self.validate_email_configuration()

        message = self._build_invitation_message(
            recipient_name=recipient_name,
            recipient_email=recipient_email,
            temporary_password=temporary_password,
            role_label=role_label,
        )
        try:
            await asyncio.to_thread(self._deliver_message, message)
        except Exception as exc:
            return {
                "sent": False,
                "message": f"Failed to send invitation email: {exc}",
            }

        return {
            "sent": True,
            "message": f"Invitation email sent to {recipient_email}.",
        }

    async def send_test_email(self, recipient_email: str) -> dict:
        self.validate_email_configuration()
        message = self._build_generic_message(
            recipient_name="Admin",
            recipient_email=recipient_email,
            subject="L&D Management Platform email configuration test",
            plain_text=(
                "This is a test email from the L&D Management Platform.\n\n"
                "If you received this email, the Outlook SMTP configuration is working."
            ),
            html=(
                "<html><body><p>This is a test email from the L&amp;D Management Platform.</p>"
                "<p>If you received this email, the Outlook SMTP configuration is working.</p></body></html>"
            ),
        )
        try:
            await asyncio.to_thread(self._deliver_message, message)
        except Exception as exc:
            return {
                "sent": False,
                "message": f"Failed to send test email: {exc}",
            }

        return {
            "sent": True,
            "message": f"Test email sent to {recipient_email}.",
        }

    def validate_email_configuration(self) -> None:
        if not self.settings.smtp_enabled:
            raise bad_request_exception("Outlook SMTP is disabled. Set SMTP_ENABLED=true to trigger emails.")
        if not self.settings.smtp_host:
            raise bad_request_exception("SMTP host is required when SMTP email sending is enabled")
        if not self.settings.smtp_sender_email:
            raise bad_request_exception("SMTP sender email is required when SMTP email sending is enabled")
        if not self.settings.smtp_username or not self.settings.smtp_password:
            raise bad_request_exception("SMTP username and password are required when SMTP email sending is enabled")

    def _build_invitation_message(
        self,
        *,
        recipient_name: str,
        recipient_email: str,
        temporary_password: str,
        role_label: str,
    ) -> EmailMessage:
        login_url = self.settings.frontend_login_url

        plain_text = (
            f"Hello {recipient_name},\n\n"
            "Your account for the internal L&D Management Platform has been created.\n\n"
            f"Role: {role_label}\n"
            f"Login email: {recipient_email}\n"
            f"Temporary password: {temporary_password}\n"
            f"Login link: {login_url}\n\n"
            "First login instructions:\n"
            "1. Sign in using the email ID and temporary password above.\n"
            "2. You will be forced to change your password before dashboard access is granted.\n"
            "3. After password reset, sign in again to access your dashboard.\n\n"
            "If you did not expect this account, contact the L&D Manager.\n"
        )
        html = f"""
        <html>
            <body>
                <p>Hello {recipient_name},</p>
                <p>Your account for the internal L&amp;D Management Platform has been created.</p>
                <p>
                    <strong>Role:</strong> {role_label}<br>
                    <strong>Login email:</strong> {recipient_email}<br>
                    <strong>Temporary password:</strong> {temporary_password}<br>
                    <strong>Login link:</strong> <a href="{login_url}">{login_url}</a>
                </p>
                <p><strong>First login instructions</strong></p>
                <p>
                    1. Sign in using the email ID and temporary password above.<br>
                    2. You will be forced to change your password before dashboard access is granted.<br>
                    3. After password reset, sign in again to access your dashboard.
                </p>
                <p>If you did not expect this account, contact the L&amp;D Manager.</p>
            </body>
        </html>
        """
        return self._build_generic_message(
            recipient_name=recipient_name,
            recipient_email=recipient_email,
            subject="Your L&D Management Platform account",
            plain_text=plain_text,
            html=html,
        )

    def _build_generic_message(
        self,
        *,
        recipient_name: str,
        recipient_email: str,
        subject: str,
        plain_text: str,
        html: str,
    ) -> EmailMessage:
        sender_name = self.settings.smtp_sender_name
        sender_email = self.settings.smtp_sender_email
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = f"{sender_name} <{sender_email}>"
        message["To"] = recipient_email
        message.set_content(plain_text)
        message.add_alternative(html, subtype="html")
        return message

    def _deliver_message(self, message: EmailMessage) -> None:
        username = self.settings.smtp_username
        password = self.settings.smtp_password

        if self.settings.smtp_use_ssl:
            with smtplib.SMTP_SSL(
                self.settings.smtp_host,
                self.settings.smtp_port,
                context=ssl.create_default_context(),
                timeout=30,
            ) as server:
                server.login(username, password)
                server.send_message(message)
            return

        with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=30) as server:
            if self.settings.smtp_use_tls:
                server.starttls(context=ssl.create_default_context())
            server.login(username, password)
            server.send_message(message)
