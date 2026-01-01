# Configuration Guide

The bot is configured using a `config.yml` file. Below is a detailed breakdown of all available options.

## Global Settings

- `debug`: (Boolean) Enable verbose debug logging.
- `admin_password`: (String) A password that allows any user to become an admin by messaging it to the bot.
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

## Admin Commands

Once a user is authenticated as an admin (by sending the `admin_password` to the bot), they can use the following commands in their direct chat with the bot:

- `/help`: Show a brief explanation of all available commands.
- `/links`: Returns a list of all mirrored channels with their Delta Chat invite links, Chat IDs, and current media settings.
- `/add CHANNEL_ID [NO_PHOTO] [NO_VIDEO]`: Adds a new Telegram channel to the mirror list. Optional flags `NO_PHOTO` and `NO_VIDEO` can be used to disable media relaying from the start.
- `/link CHAT_ID [NO_PHOTO] [NO_VIDEO]`: Updates settings for an existing channel. `CHAT_ID` is the Delta Chat Chat ID (found in `/links`). Flags `NO_PHOTO` and `NO_VIDEO` will disable the respective media types. To re-enable, simply run the command without the flags (e.g., `/link CHAT_ID`).
- `/photo CHAT_ID on|off`: Specifically enable or disable photo relaying for a channel.
- `/video CHAT_ID on|off`: Specifically enable or disable video relaying for a channel.
- `/delete CHAT_ID`: Removes a channel from the mirror list and stops mirroring it. `CHAT_ID` is the Delta Chat Chat ID.
