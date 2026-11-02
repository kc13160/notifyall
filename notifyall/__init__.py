"""
notifyall — Multi-channel Python notification library.
Zero external dependencies.
"""

from .core import Notifier
from .channels import (
    NtfyChannel,
    SlackChannel,
    TelegramChannel,
    DiscordChannel,
    EmailChannel,
)

__version__ = "0.5.1"
__author__ = "KeyZen07"

__all__ = [
    "Notifier",
    "NtfyChannel",
    "SlackChannel",
    "TelegramChannel",
    "DiscordChannel",
    "EmailChannel",
]