import smtplib, ssl
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

    context = ssl.create_default_context()
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(sender_mail, sender_password)
        server.sendmail(sender_mail, to_mail, message.as_string()) 

