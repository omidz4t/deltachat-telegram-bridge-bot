# Configuration Guide

The bot is configured using a `config.yml` file. Below is a detailed breakdown of all available options.

## Global Settings

- `debug`: (Boolean) Enable verbose debug logging.
- `logging`:
    - `level`: Log level (DEBUG, INFO, WARNING, ERROR).
    - `file`: Path to a log file (e.g., `data/bot.log`).

## Accounts

List of Delta Chat accounts the bot manages.
- `accid`: The Delta Chat account ID.
- `server`: The Delta Chat server URL.
- `use_if_exists`: If true, the bot will use this account if it's already configured.
- `proxy`:
    - `type`: `http`, `https`, `socks5`, or `ss`.
    - `host`, `port`, `username`, `password`: Connection details.

## Telegram Settings

- `api_id`, `api_hash`: Your Telegram API credentials from [my.telegram.org](https://my.telegram.org).
- `phone`: The phone number of the Telegram account.
- **Hardware/App Spoofing**:
    - `device_model`, `system_version`, `app_version`, `lang_code`: Used to make the bot appear as a specific device.

## Channels to Mirror

A list of channel configurations.
- `tgid`: (Integer/String) The Telegram channel ID (starts with -100).
- `username`: (String) Public username of the channel (used for joining).
- `chat_id`: (Integer) The Delta Chat chat ID the messages are sent to.
- `channel_photo_mode`: `auto` (sync from Telegram) or `manual`.
- `send_start`: If true, sends a "start" message to the Delta Chat channel on bot startup.
- **Media Toggles**:
    - `photo`:
        - `enable`: (Boolean) Relay photos.
        - `message`: (String) Text to send if photos are disabled.
    - `video`:
        - `enable`: (Boolean) Relay videos.
        - `message`: (String) Text to send if videos are disabled.

## History Resend Settings

- `enabled`: (Boolean) Whether to resend history to new members.
- `limit`: (Integer) The number of recent messages to resend (e.g., 10).
