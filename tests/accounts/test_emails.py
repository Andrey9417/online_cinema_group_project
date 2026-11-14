import logging
from unittest.mock import patch

from config.settings import settings
from notifications.emails import send_activation_email, send_email, send_password_reset_email
from tasks.emails import send_activation_email_task, send_password_reset_email_task


def test_send_email_builds_sendgrid_message():
    with patch("notifications.emails.sendgrid_client") as client:
        send_email("user@example.com", "Hello", "<p>Hi</p>")

    client.send.assert_called_once()
    message = client.send.call_args.args[0].get()
    assert message["from"]["email"] == settings.EMAIL_FROM
    assert message["subject"] == "Hello"
    assert message["personalizations"][0]["to"] == [{"email": "user@example.com"}]
    assert message["content"] == [{"type": "text/html", "value": "<p>Hi</p>"}]


def test_send_email_failure_is_logged_not_raised(caplog):
    with patch("notifications.emails.sendgrid_client") as client:
        client.send.side_effect = Exception("SendGrid is down")
        with caplog.at_level(logging.ERROR, logger="notifications.emails"):
            send_email("user@example.com", "Hello", "<p>Hi</p>")

    assert "user@example.com" in caplog.text


def test_send_activation_email_contains_activation_link():
    with patch("notifications.emails.send_email") as send:
        send_activation_email("user@example.com", "abc-123_XYZ")

    recipient, subject, html = send.call_args.args
    assert recipient == "user@example.com"
    assert subject == "Activate your account"
    assert f'href="{settings.API_URL}/activate?token=abc-123_XYZ"' in html


def test_send_activation_email_task_delegates_to_sender():
    with patch("tasks.emails.send_activation_email") as send:
        send_activation_email_task("user@example.com", "abc")

    send.assert_called_once_with("user@example.com", "abc")


def test_send_password_reset_email_contains_token_and_ttl():
    with patch("notifications.emails.send_email") as send:
        send_password_reset_email("user@example.com", "reset-123_XYZ")

    recipient, subject, html = send.call_args.args
    assert recipient == "user@example.com"
    assert subject == "Reset your password"
    assert "reset-123_XYZ" in html
    assert f"Valid for {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes" in html


def test_send_password_reset_email_task_delegates_to_sender():
    with patch("tasks.emails.send_password_reset_email") as send:
        send_password_reset_email_task("user@example.com", "abc")

    send.assert_called_once_with("user@example.com", "abc")
