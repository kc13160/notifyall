# Changelog

## 0.6.0 (not yet published to PyPI)

### Added
- Channels documented in the README but missing from the package: Microsoft Teams, Mattermost, Rocket.Chat, WhatsApp (Twilio) and Pushover.
- Methods documented in the README but missing from the package: `EmailChannel.send_html`, `EmailChannel.send_to_multiple`, `SlackChannel.send_blocks`, `TelegramChannel.send_photo`, `send_document` and `send_poll`, `DiscordChannel.send_embed`.
- `Notifier.from_env()` support for the new channels.
- Tests for every channel, and continuous integration with GitHub Actions.
- `LICENSE` file.

### Fixed
- Project links on PyPI that pointed to a placeholder account.
- `notifyall.__version__` now matches the package version.

## 0.0.0 to 0.5.0 (April 2026)

Published to PyPI only. The source was restored to this repository from those releases, without its earlier Git history.
