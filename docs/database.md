# Database & Message Tracking

The bot uses a SQLite database located at `data/db.sqlite` to persist channel settings and track relayed messages.

## Schema

### 1. `channels` Table
Stores configuration for each mirrored channel pair.
- `accid`: Delta Chat account ID.
- `chat_id`: Delta Chat chat ID.
- `name`: Display name.
- `photo_enabled`, `video_enabled`: Booleans (0/1).
- `photo_message`, `video_message`: Placeholder strings.
- `enabled`: Activity status (0=Paused, 1=Active).

### 2. `messages` Table
The core table for tracking every message relayed between platforms.
- `id`: Auto-incrementing internal ID.
- `telegram_msg_id`: The ID assigned by Telegram.
- `dc_msg_id`: The ID assigned by Delta Chat.
- `dc_chat_id`: Which Delta Chat channel this message belongs to.
- `text`: Content of the message.
- `media_path`, `media_type`: Details about attached files.
- `timestamp`: When the message was recorded.

### 3. `admins` Table
Stores the contact IDs of users who have successfully authenticated as administrators.
- `contact_id`: Delta Chat contact ID.

## Multi-Channel Identification

A critical aspect of the database is how it handles message IDs. 
- **Telegram IDs** are unique only within a single channel. If you mirror two channels, bot might see Message #1 from both.
- To solve this, the `messages` table uses a **Composite Unique Index**:
  ```sql
  CREATE UNIQUE INDEX idx_messages_tgid_chat ON messages(dc_chat_id, telegram_msg_id);
  ```
  This ensures the bot correctly distinguishes between Message #1 in Channel A and Message #1 in Channel B.

## Reply & Quote Resolution

When a Telegram message is a reply to another message (`reply_to_msg_id`):
1. The bot looks up the `reply_to_msg_id` in the `messages` table for that specific `dc_chat_id`.
2. It retrieves the corresponding `dc_msg_id`.
3. It sends the new message to Delta Chat using the `quoted_message_id` parameter.
This preserves the conversation context in Delta Chat!
