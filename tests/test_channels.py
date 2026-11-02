"""
Tests for the requests built by each channel. No real network call is made.
"""

import base64
import json
import os
import urllib.error
import urllib.parse
from unittest import mock

import pytest

import notifyall
from notifyall import Notifier
from notifyall.channels import (
    DiscordChannel,
    EmailChannel,
    MattermostChannel,
    NtfyChannel,
    PushoverChannel,
    RocketChatChannel,
    SlackChannel,
    TeamsChannel,
    TelegramChannel,
    WhatsAppChannel,
)


@pytest.fixture
def http():
    """Replace urlopen and record the requests sent."""
    requests = []

    def fake_urlopen(req, timeout=None):
        requests.append(req)
        response = mock.MagicMock()
        response.status = 200
        response.__enter__.return_value = response
        return response

    with mock.patch("urllib.request.urlopen", fake_urlopen):
        yield requests


def json_body(req):
    return json.loads(req.data.decode("utf-8"))


def form_body(req):
    return dict(urllib.parse.parse_qsl(req.data.decode("utf-8")))


def email_channel():
    return EmailChannel("smtp.test", 587, "user", "pass", "from@test", "to@test")


def test_all_channels_are_exported():
    for name in ("TeamsChannel", "MattermostChannel", "RocketChatChannel", "WhatsAppChannel", "PushoverChannel"):
        assert name in notifyall.__all__
        assert hasattr(notifyall, name)


def test_network_error_returns_error_result():
    channel = MattermostChannel("https://mm.test/hooks/x")
    with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("down")):
        result = channel.send("hello")
    assert result["status"] == "error"
    assert result["channel"] == "mattermost"


def test_ntfy_send(http):
    assert NtfyChannel("topic", priority="high").send("hi", title="T")["status"] == "ok"
    assert http[0].full_url == "https://ntfy.sh/topic"
    assert http[0].data == b"hi"


def test_telegram_photo(http):
    TelegramChannel("tok", "42").send_photo("https://x/p.png", caption="c")
    assert http[0].full_url == "https://api.telegram.org/bottok/sendPhoto"
    body = json_body(http[0])
    assert body["chat_id"] == "42"
    assert body["photo"] == "https://x/p.png"
    assert body["caption"] == "c"


def test_telegram_document(http):
    TelegramChannel("tok", "42").send_document("https://x/r.pdf")
    assert http[0].full_url.endswith("/sendDocument")
    assert json_body(http[0])["document"] == "https://x/r.pdf"


def test_telegram_poll(http):
    TelegramChannel("tok", "42").send_poll("Q?", ["A", "B"])
    assert http[0].full_url.endswith("/sendPoll")
    body = json_body(http[0])
    assert body["question"] == "Q?"
    assert body["options"] == [{"text": "A"}, {"text": "B"}]


def test_discord_embed(http):
    DiscordChannel("https://d.test/hook").send_embed(
        title="T", description="D", color=255,
        fields=[{"name": "n", "value": "v"}], footer="F", thumbnail_url="https://x/t.png",
    )
    embed = json_body(http[0])["embeds"][0]
    assert embed["title"] == "T"
    assert embed["color"] == 255
    assert embed["footer"] == {"text": "F"}
    assert embed["thumbnail"] == {"url": "https://x/t.png"}


def test_slack_blocks(http):
    blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": "hi"}}]
    SlackChannel("https://s.test/hook").send_blocks(blocks)
    assert json_body(http[0])["blocks"] == blocks


def test_teams_send(http):
    TeamsChannel("https://t.test/hook").send("msg", title="T")
    attachment = json_body(http[0])["attachments"][0]
    assert attachment["contentType"] == "application/vnd.microsoft.card.adaptive"
    assert [b["text"] for b in attachment["content"]["body"]] == ["T", "msg"]


def test_teams_card_facts(http):
    TeamsChannel("https://t.test/hook").send_card(
        title="T", message="m", facts=[{"name": "Env", "value": "Prod"}], color="00FF00",
    )
    body = json_body(http[0])["attachments"][0]["content"]["body"]
    assert body[-1] == {"type": "FactSet", "facts": [{"title": "Env", "value": "Prod"}]}


def test_mattermost_send(http):
    MattermostChannel("https://mm.test/hooks/x", channel="alerts").send("msg", title="T")
    body = json_body(http[0])
    assert body["text"] == "**T**\nmsg"
    assert body["channel"] == "alerts"
    assert body["username"] == "notifyall"


def test_rocketchat_send(http):
    RocketChatChannel("https://rc.test/hooks/x", alias="bot", emoji=":fire:").send("msg")
    assert json_body(http[0]) == {"text": "msg", "alias": "bot", "emoji": ":fire:"}


def test_whatsapp_send(http):
    WhatsAppChannel("ACsid", "secret", "+1555", "whatsapp:+33600").send("msg", title="T")
    req = http[0]
    assert req.full_url == "https://api.twilio.com/2010-04-01/Accounts/ACsid/Messages.json"
    assert form_body(req) == {"From": "whatsapp:+1555", "To": "whatsapp:+33600", "Body": "*T*\nmsg"}
    expected = base64.b64encode(b"ACsid:secret").decode("ascii")
    assert req.get_header("Authorization") == f"Basic {expected}"


def test_pushover_send(http):
    PushoverChannel("app", "user", priority=PushoverChannel.PRIORITY_HIGH, sound="siren").send("msg", title="T")
    body = form_body(http[0])
    assert http[0].full_url == "https://api.pushover.net/1/messages.json"
    assert body["token"] == "app"
    assert body["user"] == "user"
    assert body["priority"] == "1"
    assert body["sound"] == "siren"
    assert "retry" not in body


def test_pushover_emergency_sets_retry_and_expire(http):
    PushoverChannel("app", "user", priority=PushoverChannel.PRIORITY_EMERGENCY).send("msg")
    body = form_body(http[0])
    assert body["retry"] == "60"
    assert body["expire"] == "3600"


def test_email_html_and_multiple():
    with mock.patch("smtplib.SMTP") as smtp:
        server = smtp.return_value.__enter__.return_value
        assert email_channel().send_html("<h1>Hi</h1>", title="T")["status"] == "ok"
        _, recipients, raw = server.sendmail.call_args[0]
        assert recipients == ["to@test"]
        assert "text/html" in raw

        assert email_channel().send_to_multiple("m", ["a@test", "b@test"])["status"] == "ok"
        _, recipients, raw = server.sendmail.call_args[0]
        assert recipients == ["a@test", "b@test"]
        assert "To: a@test, b@test" in raw


def test_from_env_adds_new_channels(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    for key in list(os.environ):
        if key.startswith("NOTIFYALL_"):
            monkeypatch.delenv(key)
    monkeypatch.setenv("NOTIFYALL_TEAMS_WEBHOOK_URL", "https://t.test")
    monkeypatch.setenv("NOTIFYALL_MATTERMOST_WEBHOOK_URL", "https://m.test")
    monkeypatch.setenv("NOTIFYALL_ROCKETCHAT_WEBHOOK_URL", "https://r.test")
    monkeypatch.setenv("NOTIFYALL_WHATSAPP_ACCOUNT_SID", "s")
    monkeypatch.setenv("NOTIFYALL_WHATSAPP_AUTH_TOKEN", "t")
    monkeypatch.setenv("NOTIFYALL_WHATSAPP_FROM", "+1")
    monkeypatch.setenv("NOTIFYALL_WHATSAPP_TO", "+2")
    monkeypatch.setenv("NOTIFYALL_PUSHOVER_APP_TOKEN", "a")
    monkeypatch.setenv("NOTIFYALL_PUSHOVER_USER_KEY", "u")
    assert Notifier.from_env().channel_count == 5
