import logging
from pathlib import Path

from sendgrid import Mail, SendGridAPIClient
from jinja2 import Environment, FileSystemLoader, select_autoescape

from config.settings import settings


logger = logging.getLogger(__name__)
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "emails"
jinja = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=select_autoescape())

sendgrid_client = SendGridAPIClient(settings.SENDGRID_API_KEY)


def send_email(recipient: str, subject: str, html: str):
    message = Mail(
        from_email=settings.EMAIL_FROM,
        to_emails=recipient,
        subject=subject,
        html_content=html
    )
    try:
        sendgrid_client.send(message)
    except Exception:
        logger.exception(f"Failed to send email to {recipient}")


def send_activation_email(user_email: str, act_token: str):
    act_link = f"{settings.API_URL}/api/v1/accounts/activate?token={act_token}"
    html = jinja.get_template("activation.html").render(activation_link=act_link)
    send_email(user_email, "Activate your account", html)
