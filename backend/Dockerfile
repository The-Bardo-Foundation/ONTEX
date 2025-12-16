FROM python:3.11-slim

WORKDIR /app

# Install system dependencies if needed (e.g. for building some python packages)
# RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Environment variable for PORT should be provided by Railway, default to 8000
ENV PORT=8000

# Use shell form to allow variable expansion
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
