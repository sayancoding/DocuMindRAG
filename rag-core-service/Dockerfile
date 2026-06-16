# --- STAGE 1: Build & Dependency Compilation ---
FROM python:3.14-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Use a standard virtual env instead of the root directory layout
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# --- STAGE 2: Lightweight Production Runtime ---
FROM python:3.14-slim AS runtime

WORKDIR /app

# Best Practice: Run as a non-root user for security
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

# Copy the clean virtual environment
COPY --from=builder --chown=appuser:appuser /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Copy project files securely
COPY --chown=appuser:appuser . .

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]