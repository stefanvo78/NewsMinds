# ============================================================================
# Stage 1: Builder
# ============================================================================
# We use a multi-stage build to keep the final image small.
# This stage installs dependencies, then we copy only what's needed.

FROM python:3.12-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies needed for building Python packages
# - gcc: C compiler for some Python packages
# - libpq-dev: PostgreSQL client libraries (for psycopg2 if needed later)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first (Docker layer caching optimization)
# If requirements don't change, this layer is cached
COPY requirements.txt .

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# ============================================================================
# Stage 2: Runtime
# ============================================================================
# This is the final, smaller image that will actually run

FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install Microsoft ODBC Driver 18 for SQL Server
# Required for Azure SQL Database connectivity via aioodbc/pyodbc
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && curl -fsSL https://packages.microsoft.com/config/debian/12/prod.list | tee /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 \
    && apt-get purge -y curl gnupg \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY alembic.ini .
COPY alembic/ alembic/
COPY src/ src/
COPY scripts/docker-entrypoint.sh .

# Make entrypoint executable and create data directory
RUN chmod +x docker-entrypoint.sh && mkdir -p /app/data

# Create non-root user for security
# Running as root in containers is a security risk
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

# Expose the port the app runs on
EXPOSE 8000

# Health check - container orchestrators use this
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run entrypoint script (runs migrations then starts server)
CMD ["./docker-entrypoint.sh"]
