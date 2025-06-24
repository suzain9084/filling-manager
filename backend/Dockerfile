# Use a slim Python base image
FROM python:3.10-slim

# Install system packages (NO sudo needed here)
RUN apt-get update && apt-get install -y \
    poppler-utils \
    tesseract-ocr \
    && apt-get clean

# Set working directory
WORKDIR /backend

# Copy files
COPY . .

# Install Python dependencies
RUN pip install -r requirements.txt

# Expose port if needed (e.g. for Flask)
EXPOSE 5000

# Start the app
CMD ["python", "server.py"]
