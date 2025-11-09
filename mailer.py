from typing import List
from flask_mail import Message
from extensions import mail

def send_email(subject: str, recipients: List[str], body: str, html: str | None = None):
    if not recipients:
        return
    msg = Message(subject=subject, recipients=recipients, body=body)
    if html:
        msg.html = html
    mail.send(msg)