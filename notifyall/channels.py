"""
All notification channel implementations.
Uses only Python standard library — zero external dependencies.
"""

import base64
import json
import smtplib
import time
import urllib.error
import urllib.parse
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class BaseChannel:
    """Base class for all notification channels."""
    name = "base"

    def _post(self, url: str, data: bytes, headers: dict) -> dict:
        """POST a request body and return a standard result dict."""
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                return {"channel": self.name, "status": "ok", "code": resp.status}
        except Exception as e:
            return {"channel": self.name, "status": "error", "error": str(e)}

    def _post_json(self, url: str, payload: dict) -> dict:
        data = json.dumps(payload).encode("utf-8")
        return self._post(url, data, {"Content-Type": "application/json"})

    def _post_form(self, url: str, fields: dict, headers: dict = None) -> dict:
        data = urllib.parse.urlencode(fields).encode("utf-8")
        all_headers = {"Content-Type": "application/x-www-form-urlencoded"}
        all_headers.update(headers or {})
        return self._post(url, data, all_headers)

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


    def _api(self, method: str, payload: dict) -> dict:
        url = f"https://api.telegram.org/bot{self.bot_token}/{method}"
        return self._post_json(url, dict(payload, chat_id=self.chat_id))

    def send_photo(self, photo_url: str, caption: str = "") -> dict:
        """Send an image by URL."""
        return self._api("sendPhoto", {"photo": photo_url, "caption": caption, "parse_mode": self.parse_mode})

    def send_document(self, document_url: str, caption: str = "") -> dict:
        """Send a file by URL."""
        return self._api("sendDocument", {"document": document_url, "caption": caption, "parse_mode": self.parse_mode})

    def send_poll(self, question: str, options: list, is_anonymous: bool = True) -> dict:
        """Send a poll. Telegram requires between 2 and 10 options."""
        return self._api("sendPoll", {
            "question": question,
            "options": [{"text": option} for option in options],
            "is_anonymous": is_anonymous,
        })


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


    def send_embed(self, title: str = "", description: str = "", color: int = None, fields: list = None,
                   footer: str = "", thumbnail_url: str = "", image_url: str = "") -> dict:
        """Send a rich embed."""
        embed = {}
        if title:
            embed["title"] = title
        if description:
            embed["description"] = description
        if color is not None:
            embed["color"] = color
        if fields:
            embed["fields"] = fields
        if footer:
            embed["footer"] = {"text": footer}
        if thumbnail_url:
            embed["thumbnail"] = {"url": thumbnail_url}
        if image_url:
            embed["image"] = {"url": image_url}
        payload = {"embeds": [embed], "username": self.username}
        if self.avatar_url:
            payload["avatar_url"] = self.avatar_url
        return self._post_json(self.webhook_url, payload)


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


    def send_blocks(self, blocks: list, text: str = "") -> dict:
        """Send a Block Kit message. `text` is the fallback shown in notifications."""
        payload = {"blocks": blocks, "username": self.username, "icon_emoji": self.icon_emoji}
        if text:
            payload["text"] = text
        return self._post_json(self.webhook_url, payload)


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

    def _deliver(self, body: str, subtype: str, title: str, recipients: list) -> dict:
        msg = MIMEMultipart()
        msg["From"] = self.from_addr
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = title or "notifyall notification"
        msg.attach(MIMEText(body, subtype))
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.username, self.password)
                server.sendmail(self.from_addr, recipients, msg.as_string())
            return {"channel": self.name, "status": "ok"}
        except Exception as e:
            return {"channel": self.name, "status": "error", "error": str(e)}

    def send(self, message: str, title: str = "") -> dict:
        return self._deliver(message, "plain", title, [self.to_addr])

    def send_html(self, html: str, title: str = "") -> dict:
        """Send an HTML email to the configured recipient."""
        return self._deliver(html, "html", title, [self.to_addr])

    def send_to_multiple(self, message: str, recipients: list, title: str = "") -> dict:
        """Send one plain-text email to several recipients."""
        return self._deliver(message, "plain", title, list(recipients))


class TeamsChannel(BaseChannel):
    """Send messages to Microsoft Teams through a webhook, as Adaptive Cards."""
    name = "teams"

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def _post_card(self, body: list) -> dict:
        return self._post_json(self.webhook_url, {
            "type": "message",
            "attachments": [{
                "contentType": "application/vnd.microsoft.card.adaptive",
                "contentUrl": None,
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": body,
                },
            }],
        })

    @staticmethod
    def _text_blocks(message: str, title: str) -> list:
        body = []
        if title:
            body.append({"type": "TextBlock", "text": title, "weight": "Bolder", "size": "Medium", "wrap": True})
        if message:
            body.append({"type": "TextBlock", "text": message, "wrap": True})
        return body

    def send(self, message: str, title: str = "") -> dict:
        return self._post_card(self._text_blocks(message, title))

    def send_card(self, title: str = "", message: str = "", facts: list = None, color: str = "") -> dict:
        """
        Send a card with a table of facts ({"name": ..., "value": ...}).

        `color` is accepted for compatibility but has no effect: Adaptive Cards
        do not support arbitrary colours.
        """
        body = self._text_blocks(message, title)
        if facts:
            body.append({
                "type": "FactSet",
                "facts": [{"title": str(f["name"]), "value": str(f["value"])} for f in facts],
            })
        return self._post_card(body)


class MattermostChannel(BaseChannel):
    """Send messages via Mattermost incoming webhook."""
    name = "mattermost"

    def __init__(self, webhook_url: str, channel: str = "", username: str = "notifyall"):
        self.webhook_url = webhook_url
        self.channel = channel
        self.username = username

    def send(self, message: str, title: str = "") -> dict:
        payload = {"text": f"**{title}**\n{message}" if title else message, "username": self.username}
        if self.channel:
            payload["channel"] = self.channel
        return self._post_json(self.webhook_url, payload)


class RocketChatChannel(BaseChannel):
    """Send messages via Rocket.Chat incoming webhook."""
    name = "rocketchat"

    def __init__(self, webhook_url: str, alias: str = "notifyall", emoji: str = ":bell:"):
        self.webhook_url = webhook_url
        self.alias = alias
        self.emoji = emoji

    def send(self, message: str, title: str = "") -> dict:
        text = f"*{title}*\n{message}" if title else message
        return self._post_json(self.webhook_url, {"text": text, "alias": self.alias, "emoji": self.emoji})


class WhatsAppChannel(BaseChannel):
    """Send WhatsApp messages through the Twilio API."""
    name = "whatsapp"

    def __init__(self, account_sid: str, auth_token: str, from_number: str, to_number: str):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = self._with_prefix(from_number)
        self.to_number = self._with_prefix(to_number)

    @staticmethod
    def _with_prefix(number: str) -> str:
        return number if number.startswith("whatsapp:") else f"whatsapp:{number}"

    def send(self, message: str, title: str = "") -> dict:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        credentials = base64.b64encode(f"{self.account_sid}:{self.auth_token}".encode("utf-8")).decode("ascii")
        return self._post_form(
            url,
            {"From": self.from_number, "To": self.to_number, "Body": f"*{title}*\n{message}" if title else message},
            {"Authorization": f"Basic {credentials}"},
        )


class PushoverChannel(BaseChannel):
    """Send push notifications via Pushover."""
    name = "pushover"

    PRIORITY_LOWEST = -2
    PRIORITY_LOW = -1
    PRIORITY_NORMAL = 0
    PRIORITY_HIGH = 1
    PRIORITY_EMERGENCY = 2

    def __init__(self, app_token: str, user_key: str, priority: int = 0, sound: str = "", device: str = "",
                 retry: int = 60, expire: int = 3600):
        self.app_token = app_token
        self.user_key = user_key
        self.priority = priority
        self.sound = sound
        self.device = device
        self.retry = retry
        self.expire = expire

    def send(self, message: str, title: str = "") -> dict:
        fields = {"token": self.app_token, "user": self.user_key, "message": message, "priority": self.priority}
        if title:
            fields["title"] = title
        if self.sound:
            fields["sound"] = self.sound
        if self.device:
            fields["device"] = self.device
        if self.priority == self.PRIORITY_EMERGENCY:
            # Pushover rejects emergency messages without these two fields.
            fields["retry"] = self.retry
            fields["expire"] = self.expire
        return self._post_form("https://api.pushover.net/1/messages.json", fields)
