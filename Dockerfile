FROM python:3.11-slim

# Chrome headless for HTML→PNG rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium chromium-driver \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Output directory
RUN mkdir -p output

ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--threads", "4", "--timeout", "300", "app:app"]
