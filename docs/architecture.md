# Architecture

The Delta Chat Telegram Bridge is built with a modular architecture in Python, utilizing `telethon` for Telegram interaction and `deltachat2` for Delta Chat RPC communication.

## Core Components

### 1. Main Loop (`app/main.py`)
The entry point of the application. It handles:
- Coordinate initialization (`--init`).
- Starting the Telegram Bridge thread.
- Managing the Delta Chat event loop.
- Handling join events (`MemberAdded`, `SecureJoinQrScanSuccess`) to trigger history resending.

### 2. Telegram Bridge (`app/telegram_bridge.py`)
This component runs in a separate thread and manages the `Telethon` client.
- **Listening**: Uses Telegram's `NewMessage` events to detect content in mirrored channels.
- **Relaying**: Downloads media and sends messages to Delta Chat via the RPC interface.
- **History Fetching**: Downloads historical messages from Telegram when triggered by Delta Chat join events.
- **Syncing**: Periodically or on-demand syncs channel metadata (name, photo).

### 3. Data Models (`app/models/`)
- **`Channel`**: Represents a mirrored channel pairing, including Delta Chat `chat_id` and relay preferences.
- **`Message`**: Tracks the relationship between a Telegram Message ID and a Delta Chat Message ID.

### 4. Persistence Layer (`app/repository/`)
- **`ChannelRepository`**: Manages channel settings in the SQLite database.
- **`MessageRepository`**: Stores message mappings. This is crucial for:
    - Preventing duplicate relays.
    - Resolving replies/quotes (mapping a Telegram reply to a Delta Chat quoted message).
    - Correctly identifying "last N" messages for history resend.

### 5. Database (`app/db.py`)
Initializes the SQLite database and handles schema migrations. Uses a unique constraint on `(dc_chat_id, telegram_msg_id)` to support multiple channels where Telegram IDs might collide.

## Data Flow

1. **New Telegram Message**:
   - `TelegramBridge` detects a new message.
   - It downloads any media.
   - It checks `MessageRepository` if the Telegram message is a reply.
   - It calls `rpc.send_msg` to Delta Chat.
   - It saves the new `(telegram_id, dc_id)` pair to the database.

2. **New Delta Chat Member**:
   - `main.py` detects a `MemberAdded` or `SecurejoinInviterProgress` event.
   - It checks the local database for the last `limit` messages.
   - If local history is insufficient, it requests `TelegramBridge` to fetch more from Telegram.
   - Missing messages are relayed; existing ones are resent using `rpc.resend_messages`.
