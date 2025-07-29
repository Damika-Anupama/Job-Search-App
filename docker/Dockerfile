# Full ML mode - Local models (slower build ~10-15 min)
FROM python:3.10-slim

WORKDIR /app

# Copy full ML requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables for full ML mode
ENV APP_MODE=full-ml

# Expose the port the app runs on
EXPOSE 8000

# Command to run the uvicorn server for FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]