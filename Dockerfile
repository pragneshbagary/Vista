# Multi-stage build for VISTA Personal AI RAG System

# Stage 1: Build backend with uv
FROM python:3.12-slim as backend-builder

WORKDIR /app

# Install system dependencies and uv
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Copy project files
COPY pyproject.toml .
COPY uv.lock .
COPY vista/ ./vista/
COPY data/ ./data/
COPY api_server.py .

# Install Python dependencies with uv
RUN /root/.cargo/bin/uv sync --frozen --no-dev

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

# Copy uv from builder
COPY --from=backend-builder /root/.cargo/bin/uv /usr/local/bin/uv

# Copy virtual environment from builder
COPY --from=backend-builder /app/.venv /app/.venv

# Copy application code
COPY vista/ ./vista/
COPY data/ ./data/
COPY api_server.py .
COPY pyproject.toml .
COPY uv.lock .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production
ENV PORT=8000
ENV PATH="/app/.venv/bin:$PATH"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port
EXPOSE 8000

# Run application
CMD ["python", "api_server.py"]
