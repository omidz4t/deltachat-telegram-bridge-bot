# Use a Python base image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Set the working directory in the container
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a multi-stage-like setup
ENV UV_LINK_MODE=copy

# Install necessary system dependencies
# - libmagic1: often used by python libraries for file type identification
# - sqlite3: for database management and debugging
# - ca-certificates: for secure connections (Telegram/Delta Chat)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    sqlite3 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install the project's dependencies
# We use --mount=type=cache to speed up builds by caching the uv cache directory
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Copy the application code into the container
COPY . .

# Install the project itself
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Create a directory for persistent data
RUN mkdir -p /app/data

# Persist accounts, database, and Telegram session files
VOLUME ["/app/data"]

# Entry point for the application
# Use 'uv run' to ensure the virtual environment is used
ENTRYPOINT ["uv", "run", "python", "app/main.py"]

# Default command to run the bridge
# To initialize, run with: docker run -it -v $(pwd)/config.yml:/app/config.yml -v $(pwd)/data:/app/data <image> --init
CMD ["--run"]
