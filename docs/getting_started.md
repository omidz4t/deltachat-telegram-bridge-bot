# Getting Started

This guide walks you through setting up the **Delta Chat Telegram Bridge** from scratch — whether running locally or via Docker.

## What Gets Bridged?

The bot relays the following from Telegram to Delta Chat:

| Content Type | Behavior |
|---|---|
| **Text messages** | Relayed as-is |
| **Photos** | Downloaded and sent as attachments (configurable per channel) |
| **Videos** | Downloaded and sent as attachments (configurable per channel) |
| **Files / Documents** | Downloaded and sent (stickers, audio, PDFs, etc.) |
| **Inline URLs & Buttons** | Extracted and appended to the message text |
| **Web previews** | URL extracted and appended |
| **Replies** | Mapped to Delta Chat quoted messages (preserves conversation context) |
| **Sender name** | Shown as the override sender in Delta Chat |
| **Channel name & avatar** | Synced automatically (if `channel_photo_mode: auto`) |

Additionally, the bot supports:
- **Relay pausing** — automatically stops mirroring when the last subscriber leaves and resumes when someone joins.
- **History resend** — sends the last N messages to newly joined members.
- **Dynamic management** — add/remove channels at runtime via admin commands without restarting.

## Prerequisites

Before you begin, make sure you have the following:

| Requirement | Details |
|---|---|
| **Python** | 3.12 or higher |
| **uv** | Python package manager ([install guide](https://docs.astral.sh/uv/getting-started/installation/)) |
| **Telegram API Credentials** | `api_id` and `api_hash` from [my.telegram.org](https://my.telegram.org) |
| **Telegram Account** | A regular user account (not a bot) that has access to the channels you want to mirror |
| **Delta Chat Server** | A chatmail server URL (default: `https://nine.testrun.org`) |
| **Docker** *(optional)* | Only needed if you prefer the containerized setup |

> [!NOTE]
> This bot uses a **regular Telegram user account** via Telethon, not the Telegram Bot API. This allows it to read from private channels that your account is a member of.

---

## Step 1: Clone the Repository

```bash
git clone https://github.com/omidz4t/deltachat-telegram-bridge-bot.git
cd deltachat-telegram-bridge-bot
```

---

## Step 2: Install Dependencies

```bash
uv sync
```

This will create a virtual environment and install all required packages:
- `deltachat2[full]` — Delta Chat JSON-RPC client
- `telethon` — Telegram MTProto client
- `pyyaml` — Configuration file parser
- `python-dotenv` — Environment variable support

---

## Step 3: Get Your Telegram API Credentials

1. Go to [my.telegram.org](https://my.telegram.org) and log in with your phone number.
2. Navigate to **"API development tools"**.
3. Create a new application (name and platform don't matter).
4. Note down the `api_id` (a number) and `api_hash` (a string).

> [!IMPORTANT]
> Keep your `api_id` and `api_hash` private. Never share them publicly or commit them to version control.

---

## Step 4: Configure the Bot

Copy the example configuration file:

```bash
cp config.yml.example config.yml
```

Open `config.yml` in your editor and fill in the required values:

### Minimal Configuration

```yaml
# General Settings
debug: false
admin_password: "your_secure_password_here"
logging:
  level: INFO
  file: data/bot.log

# Delta Chat Account
accounts:
- accid: 1
  server: https://nine.testrun.org
  use_if_exists: true

# Telegram Credentials
telegram:
  api_hash: your_api_hash_here
  api_id: your_api_id_here
  phone: '+1234567890'        # your phone number with country code
  device_model: 'iPhone 12 Pro Max'  # see "Device Spoofing" below
  system_version: 'iOS 14.4'
  app_version: '8.2.2'
  lang_code: 'en'
  system_lang_code: 'en'

# Channels to Mirror
channels_to_mirror:
  - username: your_telegram_channel   # public channel: use username (without @)
    photo:
      enable: true
      message: "[Photo]"
    video:
      enable: true
      message: "[Video]"
  # For private channels, use an invite link:
  # - username: https://t.me/+ABC123xyz
  #   photo:
  #     enable: true
  #   video:
  #     enable: true

# History Resend
history_resend:
  enabled: true
  limit: 10
```

### Key Fields

| Field | Description |
|---|---|
| `admin_password` | Password to authenticate yourself as an admin via Delta Chat DM |
| `accounts[].server` | The Delta Chat (chatmail) server to create an account on |
| `telegram.api_id` / `api_hash` | Your Telegram API credentials |
| `telegram.phone` | Your Telegram phone number with country code |
| `channels_to_mirror[].username` | Public channel username (without `@`), or an **invite link** (`https://t.me/+...`) for private channels |
| `channels_to_mirror[].tgid` | Telegram channel numeric ID (starts with `-100`) — use this OR `username` |
| `telegram.device_model` | See [Device Spoofing](#device-spoofing) below |

> [!TIP]
> You don't need to know the Delta Chat `chat_id` before initialization. The bot will create broadcast channels and populate the `chat_id` field automatically during `--init`.

### Device Spoofing

The `device_model`, `system_version`, and `app_version` fields control how the bot's Telegram session appears in your **Active Sessions** list (visible in Telegram → Settings → Devices). By default it mimics an iPhone — this can help avoid suspicion if your account is monitored. You can set these to anything you like, or leave them as-is.

For the full list of configuration options, see the [Configuration Guide](configuration.md).

---

## Step 5: Initialize the Bot

Run the initialization command:

```bash
uv run python app/main.py --init
```

This interactive process will:
1. **Create a Delta Chat account** on the configured server (or reuse an existing one if `use_if_exists: true`).
2. **Authenticate your Telegram session** — you'll be prompted for a login code sent to your Telegram app (and your 2FA password if set).
3. **Join Telegram channels** — the bot will join each configured channel (public or via invite link).
4. **Create broadcast channels** in Delta Chat for each configured Telegram channel.
5. **Sync metadata** (name and avatar) from Telegram to the Delta Chat channels.
6. **Print invite links** for each broadcast channel.

> [!TIP]
> If your Delta Chat server provides a QR-based `dcaccount:` link, the bot can also configure from that — just set the server URL accordingly. This skips the manual password prompt.

After initialization completes, you'll see output like:

```
SUCCESS! Delta Chat Telegram Bridge is configured.

Broadcast Channel link for 'My Channel' (Account #1):
OPENPGP4FPR:...

You can now run the bot with: uv run python app/main.py --run
```

> [!NOTE]
> Save the invite link! You'll need it to add subscribers to your Delta Chat broadcast channel — they can scan it as a QR code or open it as a link in Delta Chat.

You can always retrieve invite links later without re-initializing:

```bash
uv run python app/main.py --link
```

---

## Step 6: Run the Bot

```bash
uv run python app/main.py --run
```

The bot will now:
- Listen for new messages in your configured Telegram channels.
- Relay text, images, videos, files, and embedded links to the corresponding Delta Chat broadcast channels.
- Preserve Telegram reply threads as Delta Chat quoted messages.
- Show the original Telegram sender's name on each message.
- Auto-pause relaying if all subscribers leave a broadcast channel, and auto-resume when someone joins.
- Automatically resend recent history when new members join (if enabled).
- Sync channel name and avatar changes from Telegram in real-time.

### Available CLI Flags

| Flag | Description |
|---|---|
| `--init` | Initialize accounts, Telegram session, and channels |
| `--run` | Start the bridge in listening mode |
| `--link` | Show invite links for configured channels (no re-init needed) |
| `--debug` | Enable verbose debug logging |

---

## Step 7: Admin Commands (Optional)

Once the bot is running, you can manage it via Delta Chat direct messages:

1. **Open a 1-on-1 chat** with the bot's Delta Chat account.
2. **Send the admin password** you configured in `config.yml` to authenticate.
3. **Use admin commands** to manage channels:

| Command | Description |
|---|---|
| `/help` | Show all available commands |
| `/links` | List all mirrored channels with invite links and media settings |
| `/add CHANNEL_ID [NO_PHOTO] [NO_VIDEO]` | Add a new channel — supports username, numeric ID, or **invite link** (`https://t.me/+...`) |
| `/link CHAT_ID [NO_PHOTO] [NO_VIDEO]` | Update media settings for an existing channel |
| `/delete CHAT_ID` | Remove a channel and stop mirroring |
| `/photo CHAT_ID on\|off` | Toggle photo relaying |
| `/video CHAT_ID on\|off` | Toggle video relaying |

> [!TIP]
> For private channels, use the **invite link** with `/add` — e.g., `/add https://t.me/+ABC123`. The bot will join the channel and start mirroring immediately, no restart required.

---

## Docker Setup (Alternative)

If you prefer running the bot in Docker, you can use the pre-built image from GitHub Container Registry or build it yourself.

### Option A: Pre-built Image

```bash
# 1. Initialize (interactive — requires terminal input for Telegram login)
docker run -it \
  -v $(pwd)/config.yml:/app/config.yml \
  -v $(pwd)/data:/app/data \
  ghcr.io/omidz4t/deltachat-telegram-bridge-bot:main --init

# 2. Run in the background
docker run -d \
  --name telegram-bridge \
  -v $(pwd)/config.yml:/app/config.yml \
  -v $(pwd)/data:/app/data \
  --restart unless-stopped \
  ghcr.io/omidz4t/deltachat-telegram-bridge-bot:main
```

### Option B: Build Locally

```bash
# Build the image
docker build -t telegram-bridge .

# Initialize (interactive)
docker run -it \
  -v $(pwd)/config.yml:/app/config.yml \
  -v $(pwd)/data:/app/data \
  telegram-bridge --init

# Run in the background
docker run -d \
  --name bridge \
  -v $(pwd)/config.yml:/app/config.yml \
  -v $(pwd)/data:/app/data \
  --restart unless-stopped \
  telegram-bridge
```

> [!IMPORTANT]
> The `--init` step **must** be run with `-it` (interactive mode) because it requires terminal input for Telegram authentication.

### Persistent Data

The `data/` directory contains all persistent state:

| Path | Contents |
|---|---|
| `data/accounts/` | Delta Chat account data and encryption keys |
| `data/db.sqlite` | SQLite database (channels, messages, admins) |
| `data/deltabot.session` | Telegram session file (Telethon) |
| `data/media/` | Downloaded photos, videos, and files (temporary relay cache) |
| `data/tg_avatar_*.png` | Cached Telegram channel avatars |
| `data/bot.log` | Log file (if configured) |

> [!CAUTION]
> Never delete the `data/` directory while the bot is running. It contains your Telegram session and Delta Chat encryption keys. Losing it means you'll need to re-initialize everything.

---

## Using a Proxy

If you need to connect through a proxy (common in regions with internet restrictions), add the `proxy` block to your account configuration:

```yaml
accounts:
- accid: 1
  server: https://nine.testrun.org
  use_if_exists: true
  proxy:
    type: http          # http, https, socks5, or ss (Shadowsocks)
    host: 127.0.0.1
    port: 1080
    username: optional_user
    password: optional_pass
```

This proxy setting applies to the **Delta Chat** connection. Telegram (via Telethon) uses its own connection settings and may require separate proxy configuration in your environment.

---

## Troubleshooting

### Bot doesn't relay messages
- Check logs in `data/bot.log` or run with `--debug` for verbose output.
- Verify your Telegram session is valid — re-run `--init` if needed.
- Ensure the Telegram channel `tgid` or `username` is correct.

### "No accounts configured" error
- You need to run `--init` before `--run`.

### Telegram authentication fails
- Double-check your `api_id`, `api_hash`, and `phone` in `config.yml`.
- If you have 2FA enabled, you'll be prompted for your password during `--init`.

### History resend not working
- Ensure `history_resend.enabled` is `true` in your config.
- Check that the Delta Chat channel is a **broadcast** type.
- Verify the bot has read access to the Telegram channel.
- See the [History Resend documentation](history_resend.md) for details.

### Permission denied on Telegram channel
- Make sure your Telegram user account is a member of the channel.
- For private channels, use the invite link format in `username` (e.g., `https://t.me/+ABC123`).

---

## What's Next?

- **[Configuration Guide](configuration.md)** — Full reference for all `config.yml` options
- **[Architecture](architecture.md)** — Understand how the bot works internally
- **[Database & Message Tracking](database.md)** — How messages are stored and tracked
- **[History Resend Logic](history_resend.md)** — Deep dive into the history sync feature
