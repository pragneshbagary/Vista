# Multi-stage build for VISTA Personal AI RAG System

# Stage 1: Build backend
FROM python:3.12-slim as backend-builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY vista/ ./vista/
COPY data/ ./data/
COPY api_server.py .

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Stage 2: Build frontend
FROM node:20-alpine as frontend-builder

WORKDIR /app/frontend

# Copy frontend files
COPY frontend/package*.json ./
COPY frontend/tsconfig.json ./
COPY frontend/next.config.mjs ./
COPY frontend/tailwind.config.js ./
COPY frontend/postcss.config.mjs ./
COPY frontend/components.json ./
COPY frontend/app ./app
COPY frontend/components ./components
COPY frontend/lib ./lib
COPY frontend/public ./public
COPY frontend/styles ./styles

# Install dependencies and build
RUN npm ci && npm run build

# Stage 3: Runtime
FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=backend-builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=backend-builder /usr/local/bin /usr/local/bin

# Copy application code
COPY vista/ ./vista/
COPY data/ ./data/
COPY api_server.py .

# Create persistence directory
RUN mkdir -p /app/chroma_db

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production
ENV PORT=8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port
EXPOSE 8000

# Run application
CMD ["python", "api_server.py"]
