FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN python -m nltk.downloader punkt punkt_tab

COPY . .

ENV ENVIRONMENT=prod

# Create a non-root user for security
RUN useradd -m appuser  

# Create the directory and set ownership BEFORE switching user
RUN mkdir -p /videoAnalytics && chown -R appuser:appuser /videoAnalytics

# Switch to the non-root user
USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]