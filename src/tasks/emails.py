from config.celery import celery_app
from notifications.emails import send_activation_email, send_password_reset_email


@celery_app.task
def send_activation_email_task(user_email: str, act_token: str):
    send_activation_email(user_email, act_token)


@celery_app.task
def send_password_reset_email_task(user_email: str, reset_token: str):
    send_password_reset_email(user_email, reset_token)
