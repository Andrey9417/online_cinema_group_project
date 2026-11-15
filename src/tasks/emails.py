from config.celery import celery_app
from notifications.emails import (
    send_activation_email,
    send_password_reset_email,
    send_comment_reply_email,
    send_comment_like_email,
)


@celery_app.task
def send_activation_email_task(user_email: str, act_token: str):
    send_activation_email(user_email, act_token)


@celery_app.task
def send_password_reset_email_task(user_email: str, reset_token: str):
    send_password_reset_email(user_email, reset_token)


@celery_app.task
def send_comment_reply_email_task(
    user_email: str, original_text: str, reply_text: str
):
    send_comment_reply_email(user_email, original_text, reply_text)


@celery_app.task
def send_comment_like_email_task(user_email: str, comment_text: str):
    send_comment_like_email(user_email, comment_text)
