# Delta Chat Telegram Bridge

A simple bot that relays messages from a Telegram channel to a Delta Chat broadcast channel. This bridge works with **regular Telegram user accounts** (not just bot accounts), allowing you to relay from private channels you are a member of.

## How it Works
1. **Listens** to a specific Telegram channel (public or private).
2. **Relays** new text, images, and videos to a Delta Chat channel.
3. **Synchronizes** (optional) the Delta Chat channel name and avatar with the Telegram source.
4. **History**: Automatically resends recent history when new members join the Delta Chat channel.

## Usage (Local)
1. **Configure**: Copy `config.yml.example` to `config.yml` and add your Telegram API credentials.
2. **Initialize**: `uv run python app/main.py --init` (Follow prompts to login).
3. **Run**: `uv run python app/main.py --run`

## Usage (Docker)
1. **Build**: 
   ```bash
   docker build -t telegram-bridge .
   ```
2. **Initialize** (Interactive setup):
   ```bash
   docker run -it -v $(pwd)/config.yml:/app/config.yml -v $(pwd)/data:/app/data telegram-bridge --init
   ```
3. **Run** (Background):
   ```bash
   docker run -d --name bridge -v $(pwd)/config.yml:/app/config.yml -v $(pwd)/data:/app/data --restart unless-stopped telegram-bridge
   ```

## Deployment
You can use the pre-built image from GitHub Container Registry:
```bash
# 1. Initialize
docker run -it \
  -v $(pwd)/config.yml:/app/config.yml \
  -v $(pwd)/data:/app/data \
  ghcr.io/omidz4t/deltachat_telegram_bridge_bot:main --init

# 2. Run
docker run -d \
  --name telegram-bridge \
  -v $(pwd)/config.yml:/app/config.yml \
  -v $(pwd)/data:/app/data \
  --restart unless-stopped \
  ghcr.io/omidz4t/deltachat_telegram_bridge_bot:main
```

## License
MIT
