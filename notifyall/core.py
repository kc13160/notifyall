"""
Notifier — the main class of notifyall.
"""

import json
import os
import threading
from datetime import datetime, timezone


def load_env_file(path: str = ".env"):
    if not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            if key and key not in os.environ:
                os.environ[key] = value


LEVELS = {
    "debug": 10,
    "info": 20,
    "success": 20,
    "warning": 30,
    "error": 40,
    "critical": 50,
}

LEVEL_LABELS = {
    "debug": ("🐛", "DEBUG"),
    "info": ("ℹ️", "INFO"),
    "success": ("✅", "SUCCESS"),
    "warning": ("⚠️", "WARNING"),
    "error": ("❌", "ERROR"),
    "critical": ("🚨", "CRITICAL"),
}


def _normalize_level(level: str) -> str:
    return (level or "info").strip().lower()


class Notifier:
    """
    Unified multi-channel notification manager.
    """

    def __init__(self, default_title: str = "", dry_run: bool = False):
        self._channels = []
        self.default_title = default_title
        self.dry_run = dry_run

        self._history = []
        self._stats = {
            "total_sends": 0,
            "success": 0,
            "errors": 0,
            "notifications_sent": 0,
        }
        self._hooks = {"before": [], "after": [], "error": []}
        self._digest_buffers = {}

    def add(self, channel, min_level: str = "info"):
        self._channels.append({
            "channel": channel,
            "min_level": _normalize_level(min_level),
        })
        return self

    def remove(self, channel):
        self._channels = [c for c in self._channels if c["channel"] != channel]
        return self

    @property
    def channel_count(self) -> int:
        return len(self._channels)

    def on(self, event: str, callback):
        if event in self._hooks:
            self._hooks[event].append(callback)
        return self

    def _fire(self, event: str, *args):
        for cb in self._hooks.get(event, []):
            try:
                cb(*args)
            except Exception:
                pass

    def _level_value(self, level: str) -> int:
        return LEVELS.get(_normalize_level(level), 20)

    def _should_send(self, min_level: str, level: str) -> bool:
        return self._level_value(level) >= self._level_value(min_level)

    def _send_one(self, channel, message: str, title: str) -> dict:
        if self.dry_run:
            result = {"channel": channel.name, "status": "ok", "dry_run": True}
        else:
            try:
                result = channel.send(message, title)
            except Exception as e:
                result = {"channel": channel.name, "status": "error", "error": str(e)}

        self._stats["total_sends"] += 1

        if result.get("status") == "ok":
            self._stats["success"] += 1
        else:
            self._stats["errors"] += 1
            self._fire("error", result)

        return result

    def _record(self, message: str, title: str, results: list, level: str):
        self._stats["notifications_sent"] += 1
        self._history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "title": title,
            "message": message,
            "level": level,
            "results": results,
        })

    def notify(self, message: str, title: str = "", level: str = "info") -> list:
        title = title or self.default_title
        level = _normalize_level(level)

        self._fire("before", message, title)

        results = []
        for entry in self._channels:
            ch = entry["channel"]
            min_level = entry["min_level"]

            if self._should_send(min_level, level):
                results.append(self._send_one(ch, message, title))
            else:
                results.append({
                    "channel": ch.name,
                    "status": "skipped",
                    "reason": f"level<{min_level}",
                })

        self._record(message, title, results, level)
        self._fire("after", message, title, results)
        return results

    def notify_parallel(self, message: str, title: str = "", level: str = "info") -> list:
        title = title or self.default_title
        level = _normalize_level(level)

        self._fire("before", message, title)

        results = [None] * len(self._channels)
        threads = []

        def _worker(idx, ch):
            results[idx] = self._send_one(ch, message, title)

        for i, entry in enumerate(self._channels):
            ch = entry["channel"]
            min_level = entry["min_level"]

            if self._should_send(min_level, level):
                t = threading.Thread(target=_worker, args=(i, ch), daemon=True)
                threads.append(t)
                t.start()
            else:
                results[i] = {
                    "channel": ch.name,
                    "status": "skipped",
                    "reason": f"level<{min_level}",
                }

        for t in threads:
            t.join(timeout=30)

        self._record(message, title, results, level)
        self._fire("after", message, title, results)
        return results

    def notify_one(self, channel_name: str, message: str, title: str = "", level: str = "info") -> dict:
        title = title or self.default_title
        level = _normalize_level(level)

        for entry in self._channels:
            ch = entry["channel"]
            min_level = entry["min_level"]

            if ch.name == channel_name:
                if not self._should_send(min_level, level):
                    return {
                        "channel": ch.name,
                        "status": "skipped",
                        "reason": f"level<{min_level}",
                    }
                return self._send_one(ch, message, title)

        return {"channel": channel_name, "status": "error", "error": "Channel not found"}

    def notify_template(self, template: str, title: str = "", level: str = "info", **kwargs) -> list:
        return self.notify(template.format(**kwargs), title=title, level=level)

    def notify_if(self, condition: bool, message: str, title: str = "", level: str = "info") -> list:
        if condition:
            return self.notify(message, title=title, level=level)
        return []

    def notify_level(self, level: str, message: str) -> list:
        level = _normalize_level(level)
        icon, label = LEVEL_LABELS.get(level, ("🔔", level.upper()))
        return self.notify(f"{icon} {message}", title=label, level=level)

    def notify_scheduled(self, message: str, title: str = "", delay_seconds: float = 0, level: str = "info") -> None:
        def _delayed():
            import time
            time.sleep(delay_seconds)
            self.notify(message, title=title, level=level)

        threading.Thread(target=_delayed, daemon=True).start()

    def notify_repeat(self, message: str, title: str = "", times: int = 1, interval: float = 60, level: str = "info") -> None:
        def _repeat():
            import time
            for _ in range(times):
                self.notify(message, title=title, level=level)
                time.sleep(interval)

        threading.Thread(target=_repeat, daemon=True).start()

    def digest(self, key: str, message: str):
        self._digest_buffers.setdefault(key, []).append(message)

    def flush_digest(self, key: str, title: str = "", level: str = "warning") -> list:
        messages = self._digest_buffers.get(key, [])
        if not messages:
            return []

        body = "\n".join(f"- {msg}" for msg in messages)
        final_message = f"{len(messages)} notifications grouped:\n{body}"
        self._digest_buffers[key] = []

        return self.notify(
            final_message,
            title=title or f"Digest: {key}",
            level=level,
        )

    @classmethod
    def from_env(cls, default_title: str = "", dry_run: bool = False):
        load_env_file()

        notifier = cls(default_title=default_title, dry_run=dry_run)

        from .channels import (
            SlackChannel,
            TelegramChannel,
            DiscordChannel,
            EmailChannel,
            NtfyChannel,
            TeamsChannel,
            MattermostChannel,
            RocketChatChannel,
            WhatsAppChannel,
            PushoverChannel,
        )

        telegram_token = os.getenv("NOTIFYALL_TELEGRAM_BOT_TOKEN")
        telegram_chat_id = os.getenv("NOTIFYALL_TELEGRAM_CHAT_ID")
        if telegram_token and telegram_chat_id:
            notifier.add(
                TelegramChannel(
                    bot_token=telegram_token,
                    chat_id=telegram_chat_id,
                ),
                min_level=os.getenv("NOTIFYALL_TELEGRAM_MIN_LEVEL", "info"),
            )

        slack_webhook = os.getenv("NOTIFYALL_SLACK_WEBHOOK_URL")
        if slack_webhook:
            notifier.add(
                SlackChannel(webhook_url=slack_webhook),
                min_level=os.getenv("NOTIFYALL_SLACK_MIN_LEVEL", "info"),
            )

        discord_webhook = os.getenv("NOTIFYALL_DISCORD_WEBHOOK_URL")
        if discord_webhook:
            notifier.add(
                DiscordChannel(webhook_url=discord_webhook),
                min_level=os.getenv("NOTIFYALL_DISCORD_MIN_LEVEL", "info"),
            )

        ntfy_topic = os.getenv("NOTIFYALL_NTFY_TOPIC")
        if ntfy_topic:
            notifier.add(
                NtfyChannel(
                    topic=ntfy_topic,
                    server=os.getenv("NOTIFYALL_NTFY_SERVER", "https://ntfy.sh"),
                    priority=os.getenv("NOTIFYALL_NTFY_PRIORITY", "default"),
                ),
                min_level=os.getenv("NOTIFYALL_NTFY_MIN_LEVEL", "info"),
            )

        smtp_host = os.getenv("NOTIFYALL_EMAIL_SMTP_HOST")
        smtp_port = os.getenv("NOTIFYALL_EMAIL_SMTP_PORT")
        smtp_user = os.getenv("NOTIFYALL_EMAIL_USERNAME")
        smtp_password = os.getenv("NOTIFYALL_EMAIL_PASSWORD")
        from_addr = os.getenv("NOTIFYALL_EMAIL_FROM")
        to_addr = os.getenv("NOTIFYALL_EMAIL_TO")

        if all([smtp_host, smtp_port, smtp_user, smtp_password, from_addr, to_addr]):
            notifier.add(
                EmailChannel(
                    smtp_host=smtp_host,
                    smtp_port=int(smtp_port),
                    username=smtp_user,
                    password=smtp_password,
                    from_addr=from_addr,
                    to_addr=to_addr,
                    use_tls=os.getenv("NOTIFYALL_EMAIL_USE_TLS", "true").lower() == "true",
                ),
                min_level=os.getenv("NOTIFYALL_EMAIL_MIN_LEVEL", "critical"),
            )

        teams_webhook = os.getenv("NOTIFYALL_TEAMS_WEBHOOK_URL")
        if teams_webhook:
            notifier.add(
                TeamsChannel(webhook_url=teams_webhook),
                min_level=os.getenv("NOTIFYALL_TEAMS_MIN_LEVEL", "info"),
            )

        mattermost_webhook = os.getenv("NOTIFYALL_MATTERMOST_WEBHOOK_URL")
        if mattermost_webhook:
            notifier.add(
                MattermostChannel(
                    webhook_url=mattermost_webhook,
                    channel=os.getenv("NOTIFYALL_MATTERMOST_CHANNEL", ""),
                ),
                min_level=os.getenv("NOTIFYALL_MATTERMOST_MIN_LEVEL", "info"),
            )

        rocketchat_webhook = os.getenv("NOTIFYALL_ROCKETCHAT_WEBHOOK_URL")
        if rocketchat_webhook:
            notifier.add(
                RocketChatChannel(webhook_url=rocketchat_webhook),
                min_level=os.getenv("NOTIFYALL_ROCKETCHAT_MIN_LEVEL", "info"),
            )

        twilio_sid = os.getenv("NOTIFYALL_WHATSAPP_ACCOUNT_SID")
        twilio_token = os.getenv("NOTIFYALL_WHATSAPP_AUTH_TOKEN")
        whatsapp_from = os.getenv("NOTIFYALL_WHATSAPP_FROM")
        whatsapp_to = os.getenv("NOTIFYALL_WHATSAPP_TO")
        if all([twilio_sid, twilio_token, whatsapp_from, whatsapp_to]):
            notifier.add(
                WhatsAppChannel(
                    account_sid=twilio_sid,
                    auth_token=twilio_token,
                    from_number=whatsapp_from,
                    to_number=whatsapp_to,
                ),
                min_level=os.getenv("NOTIFYALL_WHATSAPP_MIN_LEVEL", "info"),
            )

        pushover_token = os.getenv("NOTIFYALL_PUSHOVER_APP_TOKEN")
        pushover_user = os.getenv("NOTIFYALL_PUSHOVER_USER_KEY")
        if pushover_token and pushover_user:
            notifier.add(
                PushoverChannel(app_token=pushover_token, user_key=pushover_user),
                min_level=os.getenv("NOTIFYALL_PUSHOVER_MIN_LEVEL", "info"),
            )

        return notifier

    @property
    def history(self) -> list:
        return self._history

    def failed_notifications(self) -> list:
        return [
            entry for entry in self._history
            if any(r.get("status") == "error" for r in entry.get("results", []))
        ]

    def export_history(self, filepath: str) -> None:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self._history, f, indent=2, ensure_ascii=False)

    def clear_history(self) -> None:
        self._history.clear()

    def stats(self) -> dict:
        total = self._stats["total_sends"]
        rate = f"{100 * self._stats['success'] / total:.1f}%" if total else "N/A"
        return {
            **self._stats,
            "success_rate": rate,
            "channels_configured": self.channel_count,
        }