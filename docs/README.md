# Delta Chat Telegram Bridge Documentation

Welcome to the documentation for the **Delta Chat Telegram Bridge Bot**. This bot allows you to mirror Telegram channels into Delta Chat broadcast channels, providing a seamless bridge between the two platforms.

## Overview

The bot works by listening to new messages in a Telegram channel and relaying them to a corresponding Delta Chat broadcast channel. It also supports history synchronization, ensuring that new members joining the Delta Chat channel can see recent history from Telegram.

## Key Features

- **Real-time Mirroring**: Instantly relays text, images, videos, and other files from Telegram to Delta Chat.
- **History Resend**: Automatically sends the last `N` messages to new members who join the Delta Chat channel.
- **Multi-Channel Support**: Mirror multiple Telegram channels simultaneously using a single bot instance.
- **Proxy Support**: Configuration options for both Delta Chat (HTTP/SOCKS5) and Telegram (via Telethon).
- **Relay Pausing**: Automatically stops mirroring if the last recipient leaves the Delta Chat channel, and resumes when someone joins.
- **Media Customization**: Enable/disable photo and video relaying per channel with custom placeholder messages.
- **Automatic Sync**: Synchronizes channel name and avatar from Telegram to Delta Chat.
- **Admin Commands**: Authenticated admins can list active channel links and add new channels to mirror dynamically via Delta Chat.

## Quick Start

1. **Installation**:
   ```bash
   uv sync
   ```
2. **Configuration**:
   Copy `config.yml.example` to `config.yml` and fill in your Telegram API credentials and channel settings.
3. **Initialization**:
   Run the bot with the `--init` flag to set up your Delta Chat account and sessions.
   ```bash
   uv run python app/main.py --init
   ```
4. **Run the Bot**:
   ```bash
   uv run python app/main.py --run
   ```

## Documentation Sections

- [Architecture](architecture.md): Deep dive into the project structure and components.
- [Configuration Guide](configuration.md): Detailed explanation of all `config.yml` settings.
- [Database & Message Tracking](database.md): How the bot tracks messages and handles multi-channel IDs.
- [History Resend Logic](history_resend.md): Explanation of how the bot ensures new users get the latest content.
