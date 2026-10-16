"""Envoie par SMTP un mail "client" qui réclame un fichier au compte démo.

    python send_requests.py               # scénario au hasard
    python send_requests.py devis         # scénario précis
"""
import random
import smtplib
import sys
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

from config import DEMO_EMAIL, REPLY_TO, SENDER_EMAIL, SENDER_NAME, SMTP_HOST, SMTP_LOGIN, SMTP_PASSWORD, SMTP_PORT
from scenarios import SCENARIOS


def send_request(key=None):
    if not (SENDER_EMAIL and SMTP_LOGIN and SMTP_PASSWORD and DEMO_EMAIL):
        sys.exit("Remplis SENDER_EMAIL, SMTP_LOGIN, SMTP_PASSWORD et DEMO_EMAIL dans training_bot/.env")

    key = key or random.choice(list(SCENARIOS))
    subject, body = random.choice(SCENARIOS[key]["requests"])
    first_name = SENDER_NAME.split()[0]

    msg = EmailMessage()
    msg["From"] = formataddr((SENDER_NAME, SENDER_EMAIL))
    msg["To"] = DEMO_EMAIL
    if REPLY_TO:
        msg["Reply-To"] = formataddr((SENDER_NAME, REPLY_TO))
    msg["Subject"] = subject
    msg["Message-ID"] = make_msgid()
    msg.set_content(f"{body}\n{first_name}")

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(SMTP_LOGIN, SMTP_PASSWORD)
        smtp.send_message(msg)

    print(f"[smtp] envoyé '{subject}' ({key}) -> {DEMO_EMAIL}")
    return key, subject


if __name__ == "__main__":
    send_request(sys.argv[1] if len(sys.argv) > 1 else None)
