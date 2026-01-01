# History Resend Logic

One of the bot's most powerful features is the automatic history resending for new members. This ensures that users jumping into a broadcast channel don't see an empty screen but rather the most recent relevant content.

## How it Triggers

The bot listens for Delta Chat events that indicate a user has successfully joined or is ready to receive messages:
- `MemberAdded`: A user was added to the channel.
- `SecurejoinInviterProgress` (at 100%): A secure join handshake completed.
- `SecureJoinQrScanSuccess`: A user scanned the channel's invite QR.

## The Synchronization Process

When a join event is detected, the bot follows these steps:

1. **Check Local Database**:
   The bot queries the `messages` table for the last `limit` (e.g., 10) messages associated with that `chat_id`. It sorts them by `telegram_msg_id` to ensure correct chronological order.

2. **Validate Delta Chat Availability**:
   For each message found in the local DB, the bot checks if the message still exists in the Delta Chat core.

3. **Telegram Fetch (if needed)**:
   If the local database has fewer than `limit` "bridgeable" messages (text or media), the bot contacts Telegram.
   - It scans the Telegram channel (looking at up to 2x the limit).
   - It identifies the most recent bridgeable messages.
       - It filters out "Service Messages" (like photo updates) that cannot be mirrored.

    - **Access Fallback**: If access is denied (common for private channels where the session/cache might be stale), the bot automatically attempts to refresh its dialog list to re-establish access before retrying the fetch.


4. **Batch Resending**:
   - **Existing Messages**: If a message exists in Delta Chat, the bot uses `rpc.resend_messages` in batches to efficiently deliver them to the new user.
   - **New/Missing Messages**: If a message is found on Telegram but not locally, the bot relays it as a new message, ensuring it's captured in the local database for the next user.

## Rate Limiting & Cooldown

To prevent "join-spam" or infinite loops:
- The bot maintains a **10-second cooldown** per channel for history resending.
- It records a sync attempt immediately upon starting, ensuring multiple overlapping joins from the same handshake process don't trigger redundant Telegram fetches.

## Troubleshooting

If history is not resending:
1. **Check the logs**: Look for "Insufficient local valid history".
2. **Channel Type**: Ensure the Delta Chat channel is a "Broadcast" type.
3. **Telegram Access**: Verify the bot has permissions to read history in the Telegram channel.
