"""
Email Manager - IMAP read + SMTP send for BenX
Set env vars: BENX_EMAIL, BENX_EMAIL_PASSWORD, BENX_IMAP, BENX_SMTP
"""
import imaplib
import smtplib
import email
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from jarvis_ai.config import Config

logger = logging.getLogger(__name__)


def _decode_header_str(value: str) -> str:
    parts = decode_header(value or "")
    result = []
    for part, enc in parts:
        if isinstance(part, bytes):
            result.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            result.append(str(part))
    return " ".join(result)


class EmailManager:

    @staticmethod
    def _check_config() -> str | None:
        if not Config.EMAIL_ADDRESS or not Config.EMAIL_PASSWORD:
            return ("❌ Email not configured.\n"
                    "Set env vars: BENX_EMAIL and BENX_EMAIL_PASSWORD\n"
                    "Optional: BENX_IMAP (default: imap.gmail.com), "
                    "BENX_SMTP (default: smtp.gmail.com)")
        return None

    @staticmethod
    def read_inbox(count: int = 5, folder: str = "INBOX") -> str:
        err = EmailManager._check_config()
        if err:
            return err
        try:
            mail = imaplib.IMAP4_SSL(Config.EMAIL_IMAP)
            mail.login(Config.EMAIL_ADDRESS, Config.EMAIL_PASSWORD)
            mail.select(folder)
            _, data = mail.search(None, "ALL")
            ids = data[0].split()
            ids = ids[-count:] if len(ids) >= count else ids
            lines = [f"📧 Last {len(ids)} emails from {folder}:\n"]
            for uid in reversed(ids):
                _, msg_data = mail.fetch(uid, "(RFC822)")
                msg = email.message_from_bytes(msg_data[0][1])
                subject = _decode_header_str(msg.get("Subject", "(no subject)"))
                sender  = _decode_header_str(msg.get("From", "?"))
                date    = msg.get("Date", "?")
                lines.append(f"  • From: {sender}")
                lines.append(f"    Subject: {subject}")
                lines.append(f"    Date: {date}\n")
            mail.logout()
            return "\n".join(lines)
        except Exception as e:
            return f"❌ Email read failed: {e}"

    @staticmethod
    def read_email_body(index: int = 1, folder: str = "INBOX") -> str:
        """Read body of the Nth latest email (1 = most recent)"""
        err = EmailManager._check_config()
        if err:
            return err
        try:
            mail = imaplib.IMAP4_SSL(Config.EMAIL_IMAP)
            mail.login(Config.EMAIL_ADDRESS, Config.EMAIL_PASSWORD)
            mail.select(folder)
            _, data = mail.search(None, "ALL")
            ids = data[0].split()
            if not ids:
                return "📭 No emails found."
            uid = ids[-(index)]
            _, msg_data = mail.fetch(uid, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])
            subject = _decode_header_str(msg.get("Subject", "(no subject)"))
            sender  = _decode_header_str(msg.get("From", "?"))
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                        break
            else:
                body = msg.get_payload(decode=True).decode("utf-8", errors="replace")
            mail.logout()
            return f"📧 From: {sender}\nSubject: {subject}\n\n{body[:2000]}"
        except Exception as e:
            return f"❌ Email read failed: {e}"

    @staticmethod
    def send(to: str, subject: str, body: str) -> str:
        err = EmailManager._check_config()
        if err:
            return err
        if not to or not subject:
            return "❌ Recipient and subject are required."
        try:
            msg = MIMEMultipart()
            msg["From"]    = Config.EMAIL_ADDRESS
            msg["To"]      = to
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))
            with smtplib.SMTP(Config.EMAIL_SMTP, Config.EMAIL_SMTP_PORT) as server:
                server.ehlo()
                server.starttls()
                server.login(Config.EMAIL_ADDRESS, Config.EMAIL_PASSWORD)
                server.sendmail(Config.EMAIL_ADDRESS, to, msg.as_string())
            return f"✅ Email sent to {to}: {subject}"
        except Exception as e:
            return f"❌ Email send failed: {e}"

    @staticmethod
    def search_emails(query: str, count: int = 5) -> str:
        err = EmailManager._check_config()
        if err:
            return err
        try:
            mail = imaplib.IMAP4_SSL(Config.EMAIL_IMAP)
            mail.login(Config.EMAIL_ADDRESS, Config.EMAIL_PASSWORD)
            mail.select("INBOX")
            _, data = mail.search(None, f'SUBJECT "{query}"')
            ids = data[0].split()[-count:]
            if not ids:
                return f"🔍 No emails found matching '{query}'"
            lines = [f"🔍 Emails matching '{query}':\n"]
            for uid in reversed(ids):
                _, msg_data = mail.fetch(uid, "(RFC822)")
                msg = email.message_from_bytes(msg_data[0][1])
                subject = _decode_header_str(msg.get("Subject", "(no subject)"))
                sender  = _decode_header_str(msg.get("From", "?"))
                lines.append(f"  • {sender} — {subject}")
            mail.logout()
            return "\n".join(lines)
        except Exception as e:
            return f"❌ Email search failed: {e}"
