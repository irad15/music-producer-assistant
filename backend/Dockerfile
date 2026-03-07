# Use an official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Set work directory
WORKDIR /app

# Install uv and dependencies
RUN pip install uv
COPY pyproject.toml uv.lock* requirements.txt ./
RUN uv sync

# Copy project files
COPY . .

# Expose the port (Render sets PORT env var)
EXPOSE 8000

# API Key workaround for build (if needed) but ideally runtime only.
# Run the application
CMD ["sh", "-c", "uv run uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000}"]
