import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()
sender_mail = os.getenv("SENDER_MAIL")
sender_password = os.getenv("SENDER_PASSWORD")

def send_verification_mail(to_mail, verification_code):
    subject = "Ověřovací kód pro Discord bota"
    body = f"Tento kód použij pro ověření na serveru pomocí příkazu /verify_code {verification_code}"

    message = MIMEMultipart()
    message['From'] = sender_mail
    message['To'] = to_mail
    message['Subject'] = subject
    message.attach(MIMEText(body, 'plain'))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_mail, sender_password)
        server.sendmail(sender_mail, to_mail, message.as_string())

