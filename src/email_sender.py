"""Send HTML emails via SMTP."""

import logging
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.config import EMAIL_FROM, EMAIL_TO, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USER

logger = logging.getLogger(__name__)


def send_email(
    subject: str,
    html_body: str,
    to_addrs: str | list[str] | None = None,
) -> bool:
    """Send an HTML email via SMTP.

    Args:
        subject: Email subject line.
        html_body: HTML content of the email.
        to_addrs: Recipient(s). Defaults to config EMAIL_TO (comma-separated).

    Returns:
        True if sent successfully, False otherwise.
    """
    if to_addrs is None:
        to_addrs_str = EMAIL_TO
    elif isinstance(to_addrs, list):
        to_addrs_str = ",".join(to_addrs)
    else:
        to_addrs_str = to_addrs

    recipients = [addr.strip() for addr in to_addrs_str.split(",") if addr.strip()]
    if not recipients:
        logger.error("No recipients specified")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = ", ".join(recipients)

    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        logger.info("Connecting to SMTP server %s:%s", SMTP_HOST, SMTP_PORT)
        port = int(SMTP_PORT)
        if port == 465:
            server = smtplib.SMTP_SSL(SMTP_HOST, port, timeout=30)
        else:
            server = smtplib.SMTP(SMTP_HOST, port, timeout=30)
            server.starttls()

        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(EMAIL_FROM, recipients, msg.as_string())
        server.quit()
        logger.info("Email sent successfully to %s", recipients)
        return True

    except Exception as e:
        logger.error("Failed to send email: %s", e)
        return False


def build_subject(paper_count: int) -> str:
    """Build the email subject line.

    Format: 【MMOT论文推送】YYYY-MM-DD｜今日 N 篇论文
    """
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"【MMOT论文推送】{date_str}｜今日 {paper_count} 篇论文"
