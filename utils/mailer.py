import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()

sender_mail = os.getenv("SENDER_MAIL")
sender_password = os.getenv("SENDER_PASSWORD")

print("MAIL:", sender_mail, flush=True)
print("PASS LENGTH:", len(sender_password) if sender_password else "None", flush=True)


def send_verification_mail(to_mail, verification_code):
    subject = f"Ověřovací kód: {verification_code} | Discord server studentů VUT"

    body = f"""Dobrý den,

toto je ověřovací kód pro ověření na Discord serveru studentů VUT.

Váš ověřovací kód:
{verification_code}

Použijte jej pomocí příkazu:
/verify code {verification_code}

Pokud jste o ověření nežádali, tuto zprávu můžete ignorovat.

S pozdravem,
BizzyBot
Discord server studentů VUT
"""

    # vytvoreni emailu
    message = MIMEMultipart()
    message["From"] = sender_mail
    message["Sender"] = sender_mail
    message["Reply-To"] = sender_mail
    message["To"] = to_mail
    message["Subject"] = subject

    message.attach(MIMEText(body, "plain", "utf-8"))

    context = ssl.create_default_context()

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
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
