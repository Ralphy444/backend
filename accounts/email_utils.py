from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection


def get_sender_email():
    sender = getattr(settings, 'DEFAULT_FROM_EMAIL', '').strip()
    if sender:
        return sender

    host_user = getattr(settings, 'EMAIL_HOST_USER', '').strip()
    if host_user:
        return host_user

    return 'noreply@example.com'


def send_text_email(subject, message, recipient_list, fail_silently=False):
    recipients = [email.strip() for email in recipient_list if email and str(email).strip()]
    if not recipients:
        raise ValueError('At least one recipient email is required.')

    connection = get_connection(fail_silently=fail_silently)
    email = EmailMultiAlternatives(
        subject=subject,
        body=message,
        from_email=get_sender_email(),
        to=recipients,
        connection=connection,
    )
    return email.send()
