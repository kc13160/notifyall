"""
All notification channel implementations.
Uses only Python standard library — zero external dependencies.
"""

import json
import smtplib
import time
import urllib.error
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class BaseChannel:
    """Base class for all notification channels."""
    name = "base"

    def send(self, message: str, title: str = "") -> dict:
        raise NotImplementedError

    def send_with_retry(self, message: str, title: str = "", retries: int = 3, delay: float = 2.0) -> dict:
        """Send with automatic retry on failure."""
        last_result = None
        for attempt in range(retries + 1):
            last_result = self.send(message, title)
            if last_result.get("status") == "ok":
                return last_result
            if attempt < retries:
                time.sleep(delay)
        return last_result


class NtfyChannel(BaseChannel):
    """Send push notifications via ntfy.sh — no account required."""
    name = "ntfy"

    def __init__(self, topic: str, server: str = "https://ntfy.sh", priority: str = "default"):
        self.topic = topic
        self.server = server.rstrip("/")
        self.priority = priority

    def send(self, message: str, title: str = "") -> dict:
        url = f"{self.server}/{self.topic}"
        headers = {
            "Content-Type": "text/plain; charset=utf-8",
            "Priority": self.priority,
        }
        if title:
            headers["Title"] = title
        try:
            req = urllib.request.Request(url, data=message.encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                return {"channel": self.name, "status": "ok", "code": resp.status}
        except Exception as e:
            return {"channel": self.name, "status": "error", "error": str(e)}


class TelegramChannel(BaseChannel):
    """Send messages via Telegram bot."""
    name = "telegram"

    def __init__(self, bot_token: str, chat_id: str, parse_mode: str = "HTML", disable_preview: bool = True):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.parse_mode = parse_mode
        self.disable_preview = disable_preview

    def send(self, message: str, title: str = "") -> dict:
        text = f"<b>{title}</b>\n{message}" if title else message
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = json.dumps({
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": self.parse_mode,
            "disable_web_page_preview": self.disable_preview,
        }).encode("utf-8")
        try:
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                return {"channel": self.name, "status": "ok", "code": resp.status}
        except Exception as e:
            return {"channel": self.name, "status": "error", "error": str(e)}


class DiscordChannel(BaseChannel):
    """Send messages via Discord webhook."""
    name = "discord"

    def __init__(self, webhook_url: str, username: str = "notifyall", avatar_url: str = None):
        self.webhook_url = webhook_url
        self.username = username
        self.avatar_url = avatar_url

    def send(self, message: str, title: str = "") -> dict:
        content = f"**{title}**\n{message}" if title else message
        payload = {"content": content, "username": self.username}
        if self.avatar_url:
            payload["avatar_url"] = self.avatar_url
        data = json.dumps(payload).encode("utf-8")
        try:
            req = urllib.request.Request(self.webhook_url, data=data, headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                return {"channel": self.name, "status": "ok", "code": resp.status}
        except Exception as e:
            return {"channel": self.name, "status": "error", "error": str(e)}


class SlackChannel(BaseChannel):
    """Send messages via Slack incoming webhook."""
    name = "slack"

    def __init__(self, webhook_url: str, username: str = "notifyall", icon_emoji: str = ":bell:"):
        self.webhook_url = webhook_url
        self.username = username
        self.icon_emoji = icon_emoji

    def send(self, message: str, title: str = "") -> dict:
        text = f"*{title}*\n{message}" if title else message
        payload = {"text": text, "username": self.username, "icon_emoji": self.icon_emoji}
        data = json.dumps(payload).encode("utf-8")
        try:
            req = urllib.request.Request(self.webhook_url, data=data, headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                return {"channel": self.name, "status": "ok", "code": resp.status}
        except Exception as e:
            return {"channel": self.name, "status": "error", "error": str(e)}


class EmailChannel(BaseChannel):
    """Send notifications via email (SMTP)."""
    name = "email"

    def __init__(self, smtp_host: str, smtp_port: int, username: str, password: str,
                 from_addr: str, to_addr: str, use_tls: bool = True):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_addr = from_addr
        self.to_addr = to_addr
        self.use_tls = use_tls

    def send(self, message: str, title: str = "") -> dict:
        msg = MIMEMultipart()
        msg["From"] = self.from_addr
        msg["To"] = self.to_addr
        msg["Subject"] = title or "notifyall notification"
        msg.attach(MIMEText(message, "plain"))
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.username, self.password)
                server.sendmail(self.from_addr, self.to_addr, msg.as_string())
            return {"channel": self.name, "status": "ok"}
        except Exception as e:
            return {"channel": self.name, "status": "error", "error": str(e)}
  
