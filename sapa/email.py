"""Email notifications for SAPA."""

import json
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_config_cache: dict | None = None


def _load_email_config() -> dict | None:
    """Load email config from the SAPA config directory."""
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    from sapa.config import get_config
    config_path = get_config().config_dir / "config.json"
    if not config_path.exists():
        return None
    try:
        data = json.loads(config_path.read_text())
        _config_cache = data.get("email")
        return _config_cache
    except (json.JSONDecodeError, KeyError):
        return None


def reload_config():
    """Force reload of email config."""
    global _config_cache
    _config_cache = None


def send_notification(
    subject: str,
    body_text: str,
    recipient: str,
) -> bool:
    """Send an email notification via SMTP. Returns True on success."""
    cfg = _load_email_config()
    if not cfg:
        logger.debug("Email not configured — skipping notification")
        return False

    host = cfg.get("smtp_host")
    port = cfg.get("smtp_port", 587)
    user = cfg.get("smtp_user")
    password = cfg.get("smtp_password")
    from_addr = cfg.get("from_address", user)
    use_tls = cfg.get("smtp_tls", True)

    if not host:
        logger.warning("Email config incomplete (need smtp_host)")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = recipient

    msg.attach(MIMEText(body_text, "plain"))

    try:
        server = smtplib.SMTP(host, port, timeout=10)
        if use_tls:
            server.starttls()
        if user and password:
            server.login(user, password)
        server.sendmail(from_addr, [recipient], msg.as_string())
        server.quit()
        logger.info(f"Email sent to {recipient}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {recipient}: {e}")
        return False


def notify_new_session(
    title: str,
    file_type: str,
    topics: list[str],
    profile_name: str,
    plugin: str,
    profile_id: Optional[int] = None,
):
    """Send email notification for a newly processed session.

    Looks up recipient by profile_id in the email config. For homestead
    (family) content, sends to all addresses in homestead_recipients.
    """
    cfg = _load_email_config()
    if not cfg:
        return

    recipients: list[str] = []

    if plugin == "homestead":
        recipients = cfg.get("homestead_recipients", [])
    elif profile_id is not None:
        addr = cfg.get("recipients", {}).get(str(profile_id))
        if addr:
            recipients = [addr]

    if not recipients:
        return

    subject = f"[SAPA] New {file_type}: {title}"

    topic_str = ", ".join(topics[:10]) if topics else "none extracted"
    base_url = cfg.get("base_url", "http://localhost:8001")
    body = (
        f"New {file_type} processed for {profile_name}.\n\n"
        f"Title: {title}\n"
        f"Plugin: {plugin}\n"
        f"Topics ({len(topics)}): {topic_str}\n\n"
        f"Open SAPA: {base_url}\n"
    )

    for addr in recipients:
        send_notification(subject, body, addr)
