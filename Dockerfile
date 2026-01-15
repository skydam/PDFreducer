FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Pillow and pikepdf
RUN apt-get update && apt-get install -y \
    libjpeg62-turbo \
    libpng16-16 \
    zlib1g \
    libfreetype6 \
    && rm -rf /var/lib/apt/lists/*

# Copy application code and dependencies
COPY pyproject.toml .
COPY pdfreducer/ ./pdfreducer/

# Install Python package
RUN pip install --no-cache-dir .

# Expose web server port
EXPOSE 8000

# Run the web server (bind to 0.0.0.0 for Docker)
CMD ["pdfreducer", "--serve", "--host", "0.0.0.0", "--port", "8000"]
