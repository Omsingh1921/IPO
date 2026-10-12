# ==============================================================================
# Multi-Stage Production Dockerfile for Indian IPO Platform
# Base: Python 3.12-slim
# Security: Non-root user, minimal attack surface, health check
# ==============================================================================

# Stage 1: Build & Dependencies
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libc6-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# Stage 2: Production Runtime
FROM python:3.12-slim AS runtime

# Label metadata
LABEL maintainer="IPO Platform Engineering Team" \
      version="1.0.0" \
      description="Production Container for Indian IPO Research & Recommendation Platform"

# Set operational environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    PATH="/home/ipouser/.local/bin:$PATH" \
    TZ=Asia/Kolkata \
    REPORTS_DIR=/app/reports/daily

# Create non-root application user and group
RUN groupadd -g 1001 ipogroup && \
    useradd -u 1001 -g ipogroup -m -s /bin/sh ipouser

WORKDIR /app

# Copy installed Python packages from builder stage
COPY --from=builder /root/.local /home/ipouser/.local

# Copy application sources, configurations, and scripts
COPY --chown=ipouser:ipogroup alembic.ini ./alembic.ini
COPY --chown=ipouser:ipogroup alembic/ ./alembic/
COPY --chown=ipouser:ipogroup src/ ./src/
COPY --chown=ipouser:ipogroup tests/ ./tests/
COPY --chown=ipouser:ipogroup scripts/ ./scripts/

# Create reports and data directories with appropriate user permissions
RUN mkdir -p /app/reports/daily /app/data /app/scratch && \
    chmod +x /app/scripts/*.sh && \
    chown -R ipouser:ipogroup /app

# Switch to non-root user
USER ipouser

# Container healthcheck: validates Python runtime and CLI availability
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -m ipo_platform.cli --help > /dev/null || exit 1

# Expose reports directory volume mount
VOLUME ["/app/reports/daily"]

# Default entrypoint and command
ENTRYPOINT ["/app/scripts/start.sh"]
CMD ["python", "-m", "ipo_platform.cli", "--help"]
