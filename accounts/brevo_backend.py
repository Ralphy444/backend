"""
Custom Brevo email backend using REST API.
"""
import urllib.request
import urllib.error
import json
from django.core.mail.backends.base import BaseEmailBackend
from django.conf import settings


class BrevoEmailBackend(BaseEmailBackend):

    def send_messages(self, email_messages):
        api_key = getattr(settings, 'BREVO_API_KEY', '').strip()

        if not api_key:
            err = 'BREVO_API_KEY is not set in environment variables.'
            print(f'[BREVO] ERROR: {err}')
            if not self.fail_silently:
                raise Exception(err)
            return 0

        print(f'[BREVO] API key found: {api_key[:20]}...')

        sent = 0
        for msg in email_messages:
            try:
                to_list = [{'email': addr} for addr in msg.to]
                if not to_list:
                    continue

                from_email = msg.from_email or settings.DEFAULT_FROM_EMAIL
                if '<' in from_email:
                    parts = from_email.split('<')
                    sender = {
                        'name': parts[0].strip(),
                        'email': parts[1].strip().rstrip('>')
                    }
                else:
                    sender = {'email': from_email.strip()}

                payload = json.dumps({
                    'sender': sender,
                    'to': to_list,
                    'subject': msg.subject,
                    'textContent': msg.body,
                }).encode('utf-8')

                print(f'[BREVO] Sending to {to_list[0]["email"]}...')

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
                    result = resp.read().decode()
                    print(f'[BREVO] SUCCESS: {result}')
                sent += 1

            except urllib.error.HTTPError as e:
                error_body = e.read().decode()
                err_msg = f'HTTP {e.code}: {error_body}'
                print(f'[BREVO] HTTP ERROR: {err_msg}')
                if not self.fail_silently:
                    raise Exception(f'Brevo API error: {err_msg}')

            except urllib.error.URLError as e:
                err_msg = f'URLError: {e.reason}'
                print(f'[BREVO] URL ERROR: {err_msg}')
                if not self.fail_silently:
                    raise Exception(f'Brevo connection error: {err_msg}')

            except Exception as e:
                err_msg = f'{type(e).__name__}: {str(e)}'
                print(f'[BREVO] ERROR: {err_msg}')
                if not self.fail_silently:
                    raise

        return sent
