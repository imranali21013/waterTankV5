# ============================================================
# Water Tank System V5 - Flask Dashboard Dockerfile
# ============================================================
FROM python:3.10-slim

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5555

WORKDIR /app

# Install curl for container healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (leverages Docker layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and assets
COPY . .

# Ensure the data directory exists for SQLite database storage
RUN mkdir -p /app/data

# Expose Flask application port
EXPOSE 5555

# Healthcheck to verify the Flask server is responding
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5555/api/health || exit 1

# Launch Flask dashboard
CMD ["python", "run.py"]

