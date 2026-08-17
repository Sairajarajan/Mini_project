import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from ..config import settings

logger = logging.getLogger("aegis.email")


async def send_email(to: str, subject: str, body: str) -> bool:
    if settings.email_mode == "mock":
        logger.info(
            "\n[MOCK EMAIL] To: %s\nSubject: %s\n%s\n" + "-" * 60,
            to, subject, body,
        )
        return True

    try:
        msg = MIMEMultipart()
        msg["From"] = settings.email_sender
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(settings.email_sender, settings.email_app_password)
            server.sendmail(settings.email_sender, [to], msg.as_string())
        return True
    except Exception as exc:
        logger.error("Email send failed: %s", exc)
        return False


def alert_body(kind: str, **ctx) -> str:
    if kind == "received_toxic":
        verb = (
            "Aegis blocked this message before delivery."
            if ctx.get("blocked", True)
            else "Aegis flagged this message as inappropriate and delivered it to your child."
        )
        return (
            f"Dear Parent,\n\nYour child {ctx['child_name']} received an "
            f"inappropriate message from {ctx['sender_name']}:\n\n"
            f"\"{ctx['message']}\"\n\n"
            f"{verb}\n"
            f"Reason: {ctx['reason']}\n\n"
            f"Please talk to your child about online safety.\n\n- Aegis Guardian"
        )
    if kind == "sent_improper":
        return (
            f"Dear Parent,\n\nWe want to inform you that your child "
            f"{ctx['child_name']} attempted to send an inappropriate message:\n\n"
            f"\"{ctx['message']}\"\n\n"
            f"Aegis blocked it before delivery.\n"
            f"Reason: {ctx['reason']}\n\n"
            f"Please talk to your child about safe communication.\n\n- Aegis Guardian"
        )
    if kind == "app_inactive":
        return (
            f"Dear Parent,\n\nWe noticed that {ctx['child_name']}'s Aegis app "
            f"has not been active for over {settings.heartbeat_inactive_hours} hours. "
            f"The app may have been uninstalled.\n\n"
            f"Last seen: {ctx['last_seen']}\n\n- Aegis Guardian"
        )
    return ""