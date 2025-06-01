# user-service/Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# Expose port 8080
EXPOSE 8080

# Run Flask app
CMD ["python", "app.py"]
