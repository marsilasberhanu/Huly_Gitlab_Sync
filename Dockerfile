# Use an official lightweight Python image
FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Install system dependencies (needed for PostgreSQL drivers)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

# Expose the port your FastAPI app runs on
EXPOSE 3000

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3000", "--reload"]