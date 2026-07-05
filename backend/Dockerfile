# Backend Dockerfile for Railway deployment
# Build context: thesis_nl2sql_app/backend/ (Railway root directory)
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (gcc + libpq-dev needed for psycopg2, curl for healthcheck)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all backend source code
COPY . .

EXPOSE 8000

# Map Railway's dynamic PORT env var to API_PORT (which settings.py reads)
CMD sh -c "API_PORT=${PORT:-8000} python main.py"
