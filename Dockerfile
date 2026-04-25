FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .
COPY config.py .
COPY bot/ ./bot/
COPY db/ ./db/
COPY services/ ./services/
COPY utils/ ./utils/

# Create data directories
RUN mkdir -p data backups

# Run bot
CMD ["python", "-u", "main.py"]
