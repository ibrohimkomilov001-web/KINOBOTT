FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    python3-setuptools \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY main.py .
COPY config.py .

# Create necessary directories
RUN mkdir -p bot db services utils

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Copy application code
COPY bot/ ./bot/
COPY db/ ./db/
COPY services/ ./services/
COPY utils/ ./utils/

# Run bot
CMD ["python", "-u", "main.py"]
