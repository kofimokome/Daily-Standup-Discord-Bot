# Use a lightweight python image
FROM python:3.11-slim

# Install uv via pip to avoid external ghcr.io registry pull authentication errors
RUN pip install --no-cache-dir uv


# Set working directory
WORKDIR /app

# Copy dependency configuration files
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN uv sync --no-cache

# Copy the rest of the application code
COPY . .

# Create the data directory for SQLite database persistence
RUN mkdir -p /app/data

# Run the application
CMD ["uv", "run", "python", "main.py"]
