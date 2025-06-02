FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Set environment variables
ENV PYTHONPATH="/app:${PYTHONPATH}"

# Expose the port that dagster webserver will run on
EXPOSE 3000

# Run dagster webserver with all job files
CMD ["dagster", "dev", "-h", "0.0.0.0", "-p", "3000", "-f", "google_drive_assets.py", "-f", "slack_job.py", "-f", "web_job.py"] 