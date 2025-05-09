FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN python -m nltk.downloader punkt punkt_tab

COPY . .

ENV ENVIRONMENT=prod

# Create a non-root user for security
RUN useradd -m appuser  
USER appuser

RUN mkdir -p /videoAnalytics && chown -R appuser:appuser /videoAnalytics

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]