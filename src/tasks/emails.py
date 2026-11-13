from config.celery import celery_app
from notifications.emails import send_activation_email


@celery_app.task
def send_activation_email_task(user_email: str, act_token: str):
    send_activation_email(user_email, act_token)
