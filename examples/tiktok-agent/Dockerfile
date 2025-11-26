FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run agent
CMD ["python", "-m", "src.main"]
