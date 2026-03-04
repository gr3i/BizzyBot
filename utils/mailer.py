import os
import ssl
import smtplib
import time
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from dotenv import load_dotenv

load_dotenv()

sender_mail = os.getenv("SENDER_MAIL")
sender_password = os.getenv("SENDER_PASSWORD")


def send_verification_mail(to_mail, verification_code):
    subject = "Overeni na Discord serveru studentu VUT FP"

    body = f"""
Dekujeme za snahu o overeni na Discord serveru studentu VUT Fakulty podnikatelske.

==============================

Vas overovaci kod:

{verification_code}

==============================

Pro dokonceni overeni jej zadejte na Discordu pomoci prikazu:

/verify code {verification_code}

Tento kod je jednorazovy a slouzi pouze pro overeni vaseho uctu.

Pokud jste o overeni nezadali, muzete tuto zpravu bezpecne ignorovat.

S pozdravem
BizzyBot
Discord server studentu VUT FP
"""

    # Plain text message (less chance of SMTP/provider weirdness...)
    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = f"BizzyBot VUT FP <{sender_mail}>"
    msg["To"] = to_mail
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="seznam.cz")
    msg["Reply-To"] = sender_mail

    context = ssl.create_default_context()

    # Retry because 451 is often transient
    max_attempts = 4
    for attempt in range(1, max_attempts + 1):
        try:
            with smtplib.SMTP("smtp.seznam.cz", 587, timeout=25) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()

                server.login(sender_mail, sender_password)

                server.sendmail(sender_mail, [to_mail], msg.as_string())

            print(f"[MAIL SENT] -> {to_mail}", flush=True)
            return

        except smtplib.SMTPResponseException as e:
            # e.smtp_code, e.smtp_error
            print(f"[MAIL ERROR] attempt={attempt} code={e.smtp_code} err={e.smtp_error}", flush=True)

            # 451 = temporary, wait and retry
            if e.smtp_code == 451 and attempt < max_attempts:
                time.sleep(2 * attempt)  # 2s, 4s, 6s...
                continue

            # Other SMTP errors or last attempt
            raise

        except Exception as e:
            print(f"[MAIL ERROR] attempt={attempt} ex={e}", flush=True)
            if attempt < max_attempts:
                time.sleep(2 * attempt)
                continue
            raise
