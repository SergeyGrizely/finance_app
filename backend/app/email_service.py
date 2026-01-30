import smtplib
from email.message import EmailMessage
import os
import random

SMTP_EMAIL = os.environ.get("SMTP_EMAIL")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")

def generate_code(length=6):
    return ''.join(str(random.randint(0, 9)) for _ in range(length))

def send_code(to_email: str, code: str):
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        raise Exception("SMTP credentials not set")

    msg = EmailMessage()
    msg['Subject'] = "Ваш код подтверждения"
    msg['From'] = SMTP_EMAIL
    msg['To'] = to_email
    msg.set_content(f"Ваш код подтверждения: {code}", charset='utf-8')

    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.starttls()
        smtp.login(SMTP_EMAIL, SMTP_PASSWORD)
        smtp.send_message(msg)
