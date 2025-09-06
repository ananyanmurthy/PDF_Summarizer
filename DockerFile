# Use official Python image
FROM python:3.11-slim AS backend

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend files
COPY backend/ ./backend/

# Install Python dependencies
RUN pip install --no-cache-dir -r backend/requirements.txt

# ========================
# FRONTEND BUILD
# ========================
FROM node:18 AS frontend

WORKDIR /frontend

# Copy frontend files
COPY frontend/ ./frontend/

# Install & build React
RUN cd frontend && npm install && npm run build

# ========================
# FINAL STAGE
# ========================
FROM python:3.11-slim

WORKDIR /app

# Copy backend from first stage
COPY --from=backend /app/backend ./backend

# Copy frontend build to backend static files
COPY --from=frontend /frontend/frontend/build ./backend/static

# Install Python deps again (runtime only)
RUN pip install --no-cache-dir -r backend/requirements.txt

# Expose FastAPI port
EXPOSE 8000

# Run FastAPI
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
