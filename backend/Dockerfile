FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directory for uploads
RUN mkdir -p /tmp/uploads

# Expose port (Cloud Run will set PORT env var, default to 8080)
EXPOSE 8080

# Run application - use PORT env var or default to 8080
CMD uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080}

