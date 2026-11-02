"""
Unit tests for notifyall core functionality.
"""

import pytest
from notifyall import Notifier
from notifyall.channels import BaseChannel


class MockChannel(BaseChannel):
    """A fake channel that always succeeds — used for testing."""
    name = "mock"

    def __init__(self, fail=False):
        self.fail = fail
        self.received = []

    def send(self, message, title=""):
        self.received.append({"message": message, "title": title})
        if self.fail:
            return {"channel": self.name, "status": "error", "error": "Simulated failure"}
        return {"channel": self.name, "status": "ok"}


# ------------------------------------------------------------------ basic

def test_notify_single_channel():
    ch = MockChannel()
    n = Notifier()
    n.add(ch)
    results = n.notify("Hello")
    assert results[0]["status"] == "ok"
    assert ch.received[0]["message"] == "Hello"


def test_default_title():
    ch = MockChannel()
    n = Notifier(default_title="MyApp")
    n.add(ch)
    n.notify("Test")
    assert ch.received[0]["title"] == "MyApp"


def test_custom_title_overrides_default():
    ch = MockChannel()
    n = Notifier(default_title="Default")
    n.add(ch)
    n.notify("Test", title="Custom")
    assert ch.received[0]["title"] == "Custom"


def test_notify_multiple_channels():
    ch1 = MockChannel()
    ch2 = MockChannel()
    n = Notifier()
    n.add(ch1).add(ch2)
    results = n.notify("Multi")
    assert len(results) == 2
    assert all(r["status"] == "ok" for r in results)


# ------------------------------------------------------------------ notify_if

def test_notify_if_true():
    ch = MockChannel()
    n = Notifier()
    n.add(ch)
    results = n.notify_if(True, "Condition met")
    assert len(results) == 1


def test_notify_if_false():
    ch = MockChannel()
    n = Notifier()
    n.add(ch)
    results = n.notify_if(False, "Should not send")
    assert results == []
    assert len(ch.received) == 0


# ------------------------------------------------------------------ notify_level

def test_notify_level_success():
    ch = MockChannel()
    n = Notifier()
    n.add(ch)
    n.notify_level("success", "All good")
    assert "SUCCESS" in ch.received[0]["title"]
    assert "All good" in ch.received[0]["message"]


def test_notify_level_critical():
    ch = MockChannel()
    n = Notifier()
    n.add(ch)
    n.notify_level("critical", "System down")
    assert "CRITICAL" in ch.received[0]["title"]


# ------------------------------------------------------------------ template

def test_notify_template():
    ch = MockChannel()
    n = Notifier()
    n.add(ch)
    n.notify_template("Version {version} deployed to {env}", version="2.0", env="prod")
    assert ch.received[0]["message"] == "Version 2.0 deployed to prod"


# ------------------------------------------------------------------ parallel

def test_notify_parallel():
    ch1 = MockChannel()
    ch2 = MockChannel()
    n = Notifier()
    n.add(ch1).add(ch2)
    results = n.notify_parallel("Parallel")
    assert len(results) == 2
    assert all(r["status"] == "ok" for r in results)


# ------------------------------------------------------------------ stats

def test_stats_after_sends():
    ch = MockChannel()
    n = Notifier()
    n.add(ch)
    n.notify("A")
    n.notify("B")
    s = n.stats()
    assert s["total_sends"] == 2
    assert s["success"] == 2
    assert s["errors"] == 0
    assert s["notifications_sent"] == 2
    assert s["success_rate"] == "100.0%"


def test_stats_with_failure():
    ch = MockChannel(fail=True)
    n = Notifier()
    n.add(ch)
    n.notify("Fail")
    s = n.stats()
    assert s["errors"] == 1
    assert s["success"] == 0


# ------------------------------------------------------------------ history

def test_history_records_entries():
    ch = MockChannel()
    n = Notifier()
    n.add(ch)
    n.notify("First")
    n.notify("Second")
    assert len(n.history) == 2
    assert n.history[0]["message"] == "First"


def test_failed_notifications():
    ch = MockChannel(fail=True)
    n = Notifier()
    n.add(ch)
    n.notify("Bad")
    failed = n.failed_notifications()
    assert len(failed) == 1


def test_clear_history():
    ch = MockChannel()
    n = Notifier()
    n.add(ch)
    n.notify("Test")
    n.clear_history()
    assert n.history == []


# ------------------------------------------------------------------ hooks

def test_before_hook():
    ch = MockChannel()
    n = Notifier()
    n.add(ch)
    fired = []
    n.on("before", lambda msg, title: fired.append(msg))
    n.notify("Hook test")
    assert "Hook test" in fired


def test_after_hook():
    ch = MockChannel()
    n = Notifier()
    n.add(ch)
    fired = []
    n.on("after", lambda msg, title, results: fired.append(len(results)))
    n.notify("After hook")
    assert fired[0] == 1


# ------------------------------------------------------------------ channel_count

def test_channel_count():
    n = Notifier()
    assert n.channel_count == 0
    n.add(MockChannel())
    assert n.channel_count == 1
    n.add(MockChannel())
    assert n.channel_count == 2


def test_remove_channel():
    ch = MockChannel()
    n = Notifier()
    n.add(ch)
    n.remove(ch)
    assert n.channel_count == 0
  
