import os
import ssl
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

sender_mail = os.getenv("SENDER_MAIL")
sender_password = os.getenv("SENDER_PASSWORD")

print("MAIL:", sender_mail, flush=True)
print("PASS LENGTH:", len(sender_password) if sender_password else "None", flush=True)


def send_verification_mail(to_mail, verification_code):

    subject = "Ověření Discord serveru studentů VUT FP"

    body = f"""Dobrý den,

děkujeme za snahu o ověření na Discord serveru studentů VUT Fakulty podnikatelské.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Váš ověřovací kód:

{verification_code}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Pro dokončení ověření jej zadejte na Discordu pomocí příkazu:

/verify code {verification_code}

Tento kód je jednorázový a slouží pouze pro ověření vašeho účtu.

Pokud jste o ověření nežádali, můžete tuto zprávu bezpečně ignorovat.

S pozdravem  
BizzyBot 🤖  
Discord server studentů VUT FP
"""

    message = MIMEMultipart()
    message["From"] = f"BizzyBot – VUT FP <{sender_mail}>"
    message["To"] = to_mail
    message["Subject"] = subject

    message.attach(MIMEText(body, "plain", "utf-8"))

    context = ssl.create_default_context()

    try:
        with smtplib.SMTP("smtp.seznam.cz", 587) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()

            server.login(sender_mail, sender_password)

            server.sendmail(
                sender_mail,
                to_mail,
                message.as_string()
            )

        print(f"[MAIL SENT] -> {to_mail}", flush=True)

    except Exception as e:
        print(f"[MAIL ERROR] {e}", flush=True)
