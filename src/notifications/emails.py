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
    act_link = f"{settings.API_URL}/activate?token={act_token}"  # right now should be 404
    html = jinja.get_template("activation.html").render(activation_link=act_link)
    send_email(user_email, "Activate your account", html)


def send_password_reset_email(user_email: str, reset_token: str):
    html = jinja.get_template("password_reset.html").render(
        reset_token=reset_token,
        expire_minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES,
    )
    send_email(user_email, "Reset your password", html)


def send_comment_reply_email(user_email: str, original_text: str, reply_text: str):
    html = jinja.get_template("comment_reply.html").render(
        original_text=original_text,
        reply_text=reply_text,
    )
    send_email(user_email, "New reply to your comment", html)


def send_comment_like_email(user_email: str, comment_text: str):
    html = jinja.get_template("comment_like.html").render(comment_text=comment_text)
    send_email(user_email, "Your comment got a like", html)


def send_movie_already_purchased_email(user_email: str, movie_title: str) -> None:
    html = jinja.get_template("already_purchased.html").render(
        movie_title=movie_title,
    )
    send_email(user_email, "Movie already purchased", html)