"""
Custom Brevo (Sendinblue) email backend using their REST API.
More reliable than SMTP on cloud platforms.
"""
import urllib.request
import urllib.error
import json
from django.core.mail.backends.base import BaseEmailBackend
from django.conf import settings


class BrevoEmailBackend(BaseEmailBackend):

    def send_messages(self, email_messages):
        api_key = getattr(settings, 'BREVO_API_KEY', '')
        if not api_key:
            if not self.fail_silently:
                raise Exception('BREVO_API_KEY not set in settings.')
            return 0

        sent = 0
        for msg in email_messages:
            try:
                # Build recipients
                to_list = [{'email': addr} for addr in msg.to]
                if not to_list:
                    continue

                # Parse from email
                from_email = msg.from_email or settings.DEFAULT_FROM_EMAIL
                if '<' in from_email:
                    name_part, email_part = from_email.split('<')
                    sender = {
                        'name': name_part.strip(),
                        'email': email_part.strip().rstrip('>')
                    }
                else:
                    sender = {'email': from_email.strip()}

                payload = json.dumps({
                    'sender': sender,
                    'to': to_list,
                    'subject': msg.subject,
                    'textContent': msg.body,
                }).encode('utf-8')

                req = urllib.request.Request(
                    'https://api.brevo.com/v3/smtp/email',
                    data=payload,
                    headers={
                        'Content-Type': 'application/json',
                        'Accept': 'application/json',
                        'api-key': api_key,
                    },
                    method='POST'
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    resp.read()
                sent += 1
            except urllib.error.HTTPError as e:
                error_body = e.read().decode()
                print(f'[BREVO ERROR] HTTP {e.code}: {error_body}')
                if not self.fail_silently:
                    raise
            except Exception as e:
                print(f'[BREVO ERROR] {type(e).__name__}: {e}')
                if not self.fail_silently:
                    raise
        return sent
