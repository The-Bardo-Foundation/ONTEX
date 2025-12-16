# Stage 1: Build React Frontend
FROM node:22-alpine as build-frontend

WORKDIR /app

# Copy package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY frontend/ ./

# Build the app
RUN npm run build

# Stage 2: Python Backend
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (if any needed for postgres/etc)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY app/ ./app/

COPY --from=build-frontend /app/dist /app/app/static

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose port (Railway sets $PORT, but good to document)
EXPOSE 8000

# Run the application
# Use shell form to expand $PORT
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}

