import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()
sender_mail = os.getenv("SENDER_MAIL")
sender_password = os.getenv("SENDER_PASSWORD")

print("MAIL:", sender_mail)
print("PASS LENGTH:", len(sender_password) if sender_password else "None")

def send_verification_mail(to_mail, verification_code):
    subject = "Ověřovací kód pro Discord bota"
   body = f"""
        Dobrý den,

        toto je ověřovací kód pro Discord server studentů VUT.

        Ověřovací kód:
        {verification_code}

        Pokud jste o ověření nežádali, tuto zprávu ignorujte.

        —
        BizzyBot
        """ 

    message = MIMEMultipart()
    message['From'] = sender_mail
    message['To'] = to_mail
    message['Subject'] = subject
    message.attach(MIMEText(body, 'plain'))

    context = ssl.create_default_context()
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.ehlo()                                                   # pozdrav
        server.starttls(context=context)                                # prepnuti na TLS
        server.ehlo()                                                   # znovu pozdrav pro TLS
        server.login(sender_mail, sender_password)
        server.sendmail(sender_mail, to_mail, message.as_string()) 

