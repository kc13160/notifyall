# notifyall 🔔


[![PyPI version](https://badge.fury.io/py/notifyall.svg)](https://pypi.org/project/notifyall/)
[![Downloads](https://static.pepy.tech/badge/notifyall)](https://pepy.tech/project/notifyall)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-☕-yellow?logo=buy-me-a-coffee)](https://buymeacoffee.com/keyzen07)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-Support-blue?logo=ko-fi)](https://ko-fi.com/keyzen07)


**notifyall** is a multi-channel notification library for Python. It lets you send alerts and messages to 10 different platforms — Slack, Telegram, Discord, Email, and more — with a single unified API. It is cross-platform, requires Python 3.9+, and has **zero external dependencies**.

---

## ⚡ Installation


Install notifyall directly from PyPI with a single command. No extra dependencies are required — everything works out of the box with a standard Python installation (3.9 and above).


```bash
pip install notifyall
```


To upgrade to the latest published version if you already have notifyall installed:


```bash
pip install --upgrade notifyall
```


To verify the installation was successful and check the installed version:


```bash
python -c "import notifyall; print(notifyall.__version__)"
```


---


### Message Templates


Message templates let you define a message pattern once and fill in the dynamic values at send time using standard Python string formatting with named placeholders. This is useful when the structure of your message is always the same but the values change — deployment reports, job completions, daily summaries. It keeps your notification messages consistent and readable across your entire codebase without having to manually format strings everywhere.


```python
n.notify_template(
    "🚀 Version {version} deployed to {env} by {user}",
    version="2.1.0",
    env="production",
    user="alice"
)
```


---


### Conditional Sending


`.notify_if()` is a convenience method that combines a condition check and a notification send into a single line. Instead of wrapping every notification in an `if` statement, you pass the condition directly as the first argument. If the condition is `False`, nothing is sent and no error is raised. This keeps monitoring code clean and readable, especially when you have many threshold checks in a row.


```python
cpu_usage = 95
n.notify_if(cpu_usage > 90, f"High CPU usage: {cpu_usage}%", title="⚠️ Warning")


disk_free = 500
n.notify_if(disk_free < 1000, "Disk almost full!", title="🔴 Critical")
```


---


### Delayed and Repeated Sending


Sometimes you need to send a notification after a certain delay — for example, after a long-running background job completes, or as a scheduled reminder. `.notify_scheduled()` fires the message after a specified number of seconds without blocking your main program execution. `.notify_repeat()` is designed for recurring reminders — it sends the same message a specified number of times with a fixed interval between each send, also completely non-blocking. Both methods run in background threads so your program continues executing normally while the notifications are being sent.


```python
# Send in 30 seconds (non-blocking)
n.notify_scheduled("Scheduled task completed", delay_seconds=30)


# Send 3 times every 5 minutes (non-blocking)
n.notify_repeat("Reminder: meeting in 15 minutes", times=3, interval=300)
```


---


### Hooks (before / after / error)


Hooks are callback functions that notifyall calls automatically at specific moments in the notification lifecycle. The `before` hook is called just before sending begins, giving you the opportunity to log the outgoing message or modify it. The `after` hook is called once all channels have responded, giving you a summary of what succeeded and what failed. The `error` hook is called specifically when a channel fails, so you can handle failures independently from successes — for example, by alerting a fallback channel or writing to a log file. Hooks are completely optional and do not affect the sending process itself.


```python
def before_send(message, title):
    print(f"[notifyall] Sending: {title} — {message}")


def after_send(message, title, results):
    ok = sum(1 for r in results if r.get("status") == "ok")
    print(f"[notifyall] {ok}/{len(results)} channels OK")


def on_error(result):
    print(f"[notifyall] Error on {result['channel']}: {result['error']}")


n.on("before", before_send)
n.on("after",  after_send)
n.on("error",  on_error)
```


---


### Automatic Retry


Network failures are temporary by nature — a webhook endpoint might be briefly unreachable due to a server restart, a rate limit, or a transient network issue. The automatic retry system handles this transparently: when a send fails, notifyall waits a configurable number of seconds and tries again, up to a maximum number of attempts. This dramatically improves reliability in unstable network environments without requiring any extra logic in your code. Retry is available directly on individual channel objects via `.send_with_retry()`.


```python
from notifyall.channels import SlackChannel


ch = SlackChannel(webhook_url="...")
result = ch.send_with_retry("Important message", retries=3, delay=2.0)
# Retries up to 3 times with 2 seconds between attempts
```


---


### Statistics


The statistics system gives you a real-time overview of your notifier's activity. After sending any number of notifications, you can call `.stats()` to get a breakdown of how many messages were sent, how many succeeded, how many failed, and your overall success rate. This is useful for monitoring the health of your notification system itself — if your success rate drops below 100%, you know something is wrong with one of your channels and can investigate before a critical alert gets lost.


```python
n.notify("Deployment 1")
n.notify("Deployment 2")
n.notify("Deployment 3")


print(n.stats())
# {
#   "total_sends": 9,
#   "success": 9,
#   "errors": 0,
#   "success_rate": "100.0%",
#   "notifications_sent": 3,
#   "channels_configured": 3
# }
```


---


### History and Export


Every notification sent through the notifier is automatically recorded in an in-memory history log. Each entry includes the timestamp, the title, the message, and the result for each channel. You can inspect the history at any time to audit what was sent and when, filter only the failed notifications for debugging, or export the entire history to a JSON file for long-term storage or external analysis. The history can also be cleared at any point to free memory or start a fresh recording session.


```python
# View the last 5 notifications
for entry in n.history[-5:]:
    print(f"[{entry['timestamp']}] {entry['title']} — {entry['message']}")


# View failed notifications only
for entry in n.failed_notifications():
    print(entry)


# Export full history to JSON
n.export_history("notifications.json")


# Clear history
n.clear_history()
```


---


## 🔧 Channel Configuration


### Email (Gmail, Outlook, etc.)


The email channel uses Python's built-in `smtplib` to send notifications via any standard SMTP server — Gmail, Outlook, Yahoo, or your own self-hosted mail server. You configure it with your SMTP credentials and the sender/recipient addresses. Beyond plain text messages, the email channel supports HTML formatting for rich layouts, and bulk sending to multiple recipients in a single call. TLS encryption is supported and recommended for all production use.


```python
from notifyall.channels import EmailChannel


ch = EmailChannel(
    smtp_host="smtp.gmail.com",
    smtp_port=587,
    username="me@gmail.com",
    password="app_password",
    from_addr="me@gmail.com",
    to_addr="recipient@email.com",
    use_tls=True
)


ch.send("Hello!", title="Email Test")
ch.send_html("<h1>Hello</h1><p>HTML message</p>", title="HTML Email")
ch.send_to_multiple("Grouped message", ["alice@mail.com", "bob@mail.com"])
```


> 💡 For Gmail, enable 2-step verification and create an **app password** in your Google account settings.


---


### Slack


The Slack channel sends messages to any Slack workspace via an Incoming Webhook URL. You can customize the bot's display name and avatar emoji. For basic use, `.send()` posts a plain text message. For teams that need rich formatting, `.send_blocks()` accepts a full Slack Block Kit payload, giving you headers, bold text, sections, dividers, buttons, and any other layout element that the Slack API supports.


```python
from notifyall.channels import SlackChannel


ch = SlackChannel(
    webhook_url="https://hooks.slack.com/services/XXX/YYY/ZZZ",
    username="notifyall",
    icon_emoji=":bell:"
)


ch.send("Deployment successful", title="Prod")


# With Block Kit (advanced formatting)
ch.send_blocks([
    {"type": "header", "text": {"type": "plain_text", "text": "🚀 Alert"}},
    {"type": "section", "text": {"type": "mrkdwn", "text": "*Deployment* successful ✅"}}
])
```


> 💡 Create an Incoming Webhook on [api.slack.com/apps](https://api.slack.com/apps).


---


### Telegram


The Telegram channel sends messages to any Telegram chat, group, or channel via the Telegram Bot API. You configure it with a bot token (obtained from @BotFather) and a chat ID. It supports HTML and Markdown formatting for styled messages, link preview control, and several advanced methods: sending photos with captions, sending file attachments, and even creating polls directly in the chat — all without leaving your Python code.


```python
from notifyall.channels import TelegramChannel


ch = TelegramChannel(
    bot_token="123456789:ABCdefGHIjklMNOpqrSTUvwxYZ",
    chat_id="-100123456789",
    parse_mode="HTML",
    disable_preview=True
)


ch.send("Hello from notifyall!", title="Test")
ch.send_photo("https://example.com/image.png", caption="Today's chart")
ch.send_document("https://example.com/report.pdf", caption="Monthly report")
ch.send_poll("Are you satisfied?", ["Yes", "No", "Maybe"])
```


> 💡 Create a bot with [@BotFather](https://t.me/BotFather) on Telegram to get your token.


---


### Discord


The Discord channel sends messages to any Discord server channel via a webhook URL. You can set a custom bot username and avatar image. For basic alerts, `.send()` sends a plain text message. For more professional looking notifications, `.send_embed()` lets you build a rich embed with a title, description, color, structured fields displayed side by side, a footer, and a thumbnail image — the same format used by most Discord bots and integrations.


```python
from notifyall.channels import DiscordChannel


ch = DiscordChannel(
    webhook_url="https://discord.com/api/webhooks/XXX/YYY",
    username="notifyall",
    avatar_url="https://example.com/avatar.png"
)


ch.send("Simple message")


# Rich embed
ch.send_embed(
    title="Deployment Report",
    description="Version 2.0 is now live",
    color=0x00ff00,
    fields=[
        {"name": "Environment", "value": "Production", "inline": True},
        {"name": "Duration", "value": "2m 34s", "inline": True}
    ],
    footer="notifyall v0.3.0",
    thumbnail_url="https://example.com/logo.png"
)
```


> 💡 Create a webhook in your Discord server settings → Integrations.


---


### Ntfy (100% free, no account)


Ntfy is a completely free, open-source push notification service that requires absolutely no account and no sign-up. You choose a topic name (a unique string that acts like a channel identifier), configure the channel with that topic, and subscribe to it on your phone using the ntfy app. Notifications arrive as native push notifications on Android and iOS. It is by far the easiest channel to set up for personal projects and self-hosted infrastructure. You can also self-host the ntfy server for maximum privacy.


```python
from notifyall.channels import NtfyChannel


ch = NtfyChannel(
    topic="my-secret-topic-xyz",
    server="https://ntfy.sh",
    priority="high"
)
ch.send("Free push notification!", title="Ntfy Test")
```


> 💡 Install the [ntfy](https://ntfy.sh) app on your phone and subscribe to your topic. No account required.


---


### Microsoft Teams


The Microsoft Teams channel sends messages to a Teams channel via a webhook. Plain text messages work out of the box with `.send()`. For enterprise use cases where more structured information is needed, `.send_card()` generates a rich adaptive card with a title, a description message, and a table of key-value facts — useful for deployment reports, incident summaries, or any structured status update that needs to be clearly readable in a busy Teams channel.


```python
from notifyall.channels import TeamsChannel


ch = TeamsChannel(webhook_url="https://your-teams-webhook-url")


ch.send("Simple message", title="Alert")


# Rich card with facts
ch.send_card(
    title="Deployment Report",
    message="Version 2.0 deployed successfully",
    facts=[
        {"name": "Environment", "value": "Production"},
        {"name": "Duration", "value": "2 minutes"}
    ],
    color="00FF00"
)
```


> 💡 Create a webhook with the Workflows app in Teams. Messages are sent as Adaptive Cards, which do not support custom colours, so `color` currently has no effect.


---


### Mattermost


Mattermost is a self-hosted, open-source alternative to Slack widely used in enterprise and privacy-sensitive environments. The Mattermost channel works exactly like the Slack channel — you provide a webhook URL, optionally set a target channel and bot username, and send messages normally. This makes it easy to migrate existing Slack integrations to Mattermost without changing any of your notification logic.


```python
from notifyall.channels import MattermostChannel


ch = MattermostChannel(
    webhook_url="https://your-instance.mattermost.com/hooks/XXX",
    channel="alerts",
    username="notifyall"
)
ch.send("Deployment successful", title="Prod")
```


---


### Rocket.Chat


Rocket.Chat is another popular self-hosted team messaging platform used heavily in DevOps and open-source communities. The Rocket.Chat channel connects via an Incoming Webhook and lets you set a custom display alias and emoji icon for the bot. It integrates seamlessly with existing Rocket.Chat workspaces and supports the same message format as other webhook-based channels.


```python
from notifyall.channels import RocketChatChannel


ch = RocketChatChannel(
    webhook_url="https://your-instance.rocket.chat/hooks/XXX",
    alias="notifyall",
    emoji=":bell:"
)
ch.send("System alert", title="Monitoring")
```


---


### WhatsApp (via Twilio)


The WhatsApp channel sends messages to any WhatsApp number using the Twilio API. Because WhatsApp does not offer a direct public API for programmatic messaging, Twilio acts as the intermediary. You need a Twilio account, an approved WhatsApp sender number, and the recipient's WhatsApp number. Twilio offers a free sandbox for testing before going live. This channel is ideal for reaching non-technical stakeholders who prefer WhatsApp over developer-focused platforms.


```python
from notifyall.channels import WhatsAppChannel


ch = WhatsAppChannel(
    account_sid="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    auth_token="your_auth_token",
    from_number="whatsapp:+14155238886",
    to_number="whatsapp:+33612345678"
)
ch.send("Critical alert!", title="Monitoring")
```


> 💡 Requires a [Twilio](https://twilio.com) account. A free sandbox is available for testing.


---


### Pushover


Pushover is a dedicated push notification service for developers that delivers native notifications to iOS and Android devices with fine-grained control over priority, sound, and device targeting. You register an application on pushover.net to get an app token, then use your personal user key to receive notifications on your devices. The `PRIORITY_HIGH` setting makes the notification bypass quiet hours and sound even when the device is silenced — useful for truly critical alerts.


```python
from notifyall.channels import PushoverChannel


ch = PushoverChannel(
    app_token="azGDORePK8gMaC0QOYAMyEEuzJnyUi",
    user_key="uQiRzpo4DXghDmr9QzzfQu27cmVRsG",
    priority=PushoverChannel.PRIORITY_HIGH,
    sound="siren"
)
ch.send("Server is down!", title="🚨 CRITICAL")
```


> 💡 Create an application on [pushover.net](https://pushover.net) to get your app token.


---


### Configuration from environment variables


`Notifier.from_env()` reads a `.env` file and the environment, and adds every channel that is fully configured.


```python
from notifyall import Notifier

n = Notifier.from_env(default_title="My app")
n.notify("Hello!")
```


| Channel | Variables |
|---|---|
| Telegram | `NOTIFYALL_TELEGRAM_BOT_TOKEN`, `NOTIFYALL_TELEGRAM_CHAT_ID` |
| Slack | `NOTIFYALL_SLACK_WEBHOOK_URL` |
| Discord | `NOTIFYALL_DISCORD_WEBHOOK_URL` |
| Ntfy | `NOTIFYALL_NTFY_TOPIC`, optional `NOTIFYALL_NTFY_SERVER`, `NOTIFYALL_NTFY_PRIORITY` |
| Email | `NOTIFYALL_EMAIL_SMTP_HOST`, `NOTIFYALL_EMAIL_SMTP_PORT`, `NOTIFYALL_EMAIL_USERNAME`, `NOTIFYALL_EMAIL_PASSWORD`, `NOTIFYALL_EMAIL_FROM`, `NOTIFYALL_EMAIL_TO`, optional `NOTIFYALL_EMAIL_USE_TLS` |
| Teams | `NOTIFYALL_TEAMS_WEBHOOK_URL` |
| Mattermost | `NOTIFYALL_MATTERMOST_WEBHOOK_URL`, optional `NOTIFYALL_MATTERMOST_CHANNEL` |
| Rocket.Chat | `NOTIFYALL_ROCKETCHAT_WEBHOOK_URL` |
| WhatsApp | `NOTIFYALL_WHATSAPP_ACCOUNT_SID`, `NOTIFYALL_WHATSAPP_AUTH_TOKEN`, `NOTIFYALL_WHATSAPP_FROM`, `NOTIFYALL_WHATSAPP_TO` |
| Pushover | `NOTIFYALL_PUSHOVER_APP_TOKEN`, `NOTIFYALL_PUSHOVER_USER_KEY` |


Each channel also accepts `NOTIFYALL_<CHANNEL>_MIN_LEVEL`. The default is `info`, except email, which defaults to `critical`.


---


## 🛠️ Real-World Use Cases


### Server Monitoring


This example uses the `psutil` library to read real-time system metrics and sends alerts only when thresholds are exceeded. The key advantage of using notifyall here is that a single call to `.notify_if()` handles both the condition check and the multi-channel delivery — no boilerplate, no nested `if` blocks. Run this script as a cron job or a background daemon to get proactive alerts before a server problem becomes a full outage.


```python
import psutil
from notifyall import Notifier
from notifyall.channels import TelegramChannel, SlackChannel


n = Notifier(default_title="🖥️ Monitoring")
n.add(TelegramChannel(bot_token="...", chat_id="..."))
n.add(SlackChannel(webhook_url="..."))


cpu = psutil.cpu_percent()
mem = psutil.virtual_memory().percent
disk = psutil.disk_usage("/").percent


n.notify_if(cpu > 90,  f"Critical CPU usage: {cpu}%")
n.notify_if(mem > 85,  f"High RAM usage: {mem}%")
n.notify_if(disk > 95, f"Disk almost full: {disk}%")
```


---


### CI/CD Pipeline


Integrating notifyall into a CI/CD pipeline gives your whole team instant visibility into deployments without having to check a dashboard. The `try/except` pattern shown here covers the two most important cases: a successful deployment sends a templated success message with the version and environment filled in automatically, while any unexpected exception triggers a critical alert with the full error message so you can diagnose the problem immediately.


```python
from notifyall import Notifier
from notifyall.channels import SlackChannel, TeamsChannel


n = Notifier()
n.add(SlackChannel(webhook_url="..."))
n.add(TeamsChannel(webhook_url="..."))


try:
    deploy()
    n.notify_template("✅ v{version} deployed to {env}!", version="2.0", env="prod")
except Exception as e:
    n.notify_level("critical", f"Deployment failed: {e}")
```


---


### Daily Automated Report


Using the `schedule` library alongside notifyall, you can build a fully automated reporting system that runs indefinitely and delivers a daily digest to your inbox and your phone at a specific time every morning. The report content can be anything — database queries, API calls, file statistics — just build the message string and pass it to `.notify()`. The `schedule.every().day.at()` syntax makes the timing human-readable and easy to adjust.


```python
import schedule
import time
from notifyall import Notifier
from notifyall.channels import EmailChannel, TelegramChannel


n = Notifier(default_title="📊 Daily Report")
n.add(EmailChannel(...))
n.add(TelegramChannel(...))


def report():
    n.notify("Today's sales: €1,234\nNew customers: 42\nResolved tickets: 18")


schedule.every().day.at("08:00").do(report)


while True:
    schedule.run_pending()
    time.sleep(60)
```


---


### Trading Alert


In algorithmic trading, speed and reliability of alerts are critical. This example shows a price monitoring function that fires a notification the moment a target price is reached. Using notifyall here means the alert is simultaneously delivered to Telegram for mobile visibility and Discord for team awareness, with a single function call. The `.notify_if()` pattern keeps the alert logic minimal so it can be called on every price tick without adding latency.


```python
from notifyall import Notifier
from notifyall.channels import TelegramChannel, DiscordChannel


n = Notifier(default_title="📈 Trading Bot")
n.add(TelegramChannel(bot_token="...", chat_id="..."))
n.add(DiscordChannel(webhook_url="..."))


def check_price(symbol, price, target):
    n.notify_if(
        price >= target,
        f"{symbol} reached €{price} (target: €{target}) 🎯",
        title="Buy Signal"
    )
```


---


## 🧪 Tests


The test suite covers the notifier and the requests built by each channel, using mocked network calls. Run it with pytest before contributing or after modifying the source code to make sure everything still works as expected.


```bash
pip install pytest
pytest tests/
```


---


## ✅ Zero External Dependencies


`notifyall` uses **only the Python standard library**. This means you never have to worry about dependency conflicts, security vulnerabilities in third-party packages, or broken installs. Every feature — HTTP requests, email sending, parallel threads, JSON serialization — is implemented using modules that ship with every Python installation, with no external packages required at runtime.


| Module | Usage |
|---|---|
| `smtplib` | Sending emails |
| `urllib` | HTTP requests to APIs |
| `json` | Payload serialization |
| `threading` | Non-blocking parallel sending |
| `base64` | Basic authentication (WhatsApp) |
| `time` | Retry, delays, timestamps |
| `os` | `.env` file loading |


---


## 🤝 Contributing


Contributions are welcome!


1. Fork the project
2. Create a branch (`git checkout -b feature/new-channel`)
3. Commit your changes (`git commit -m "feat: add XYZ channel"`)
4. Push your branch (`git push origin feature/new-channel`)
5. Open a Pull Request


**Contribution ideas:**
- New channel (Pushbullet, Signal, Matrix, Gotify...)
- More unit tests
- Integration with Python standard `logging`
- Async/await support


---


## ☕ Support the Project


`notifyall` is **100% free and open source** (MIT). If this library saves you time, buying me a coffee is always appreciated! 🙏


| Platform | Link |
|---|---|
| ☕ Buy Me a Coffee | [buymeacoffee.com/keyzen07](https://buymeacoffee.com/keyzen07) |
| 🍵 Ko-fi | [ko-fi.com/keyzen07](https://ko-fi.com/keyzen07) |


Your support helps:
- 🔧 Maintain and fix the library
- ➕ Add new channels
- 📖 Improve documentation
- ⚡ Build new features


Thanks to all contributors and supporters 💙


---


## 📄 License


MIT — Free to use in personal and commercial projects.
