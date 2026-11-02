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
    TeamsChannel,
    MattermostChannel,
    RocketChatChannel,
    WhatsAppChannel,
    PushoverChannel,
)

__version__ = "0.6.0"
__author__ = "KeyZen07"

__all__ = [
    "Notifier",
    "NtfyChannel",
    "SlackChannel",
    "TelegramChannel",
    "DiscordChannel",
    "EmailChannel",
    "TeamsChannel",
    "MattermostChannel",
    "RocketChatChannel",
    "WhatsAppChannel",
    "PushoverChannel",
]
