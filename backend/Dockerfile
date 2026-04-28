FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r /app/requirements.txt
RUN pip install --no-cache-dir gunicorn

# Copy application code
COPY . /app

EXPOSE 10000

# Use gunicorn for production-like server and honor platform-provided PORT
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-10000} app:app --workers 1 --threads 4 --timeout 120"]
