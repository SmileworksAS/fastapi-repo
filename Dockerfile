# Bruk et lett, men fullverdig Python-image
FROM python:3.11-slim

# Sett arbeidskatalog
WORKDIR /app

# Kopier kun requirements først (for cache-effektivitet)
COPY requirements.txt .

# Installer dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Lag persistent data-mappe
RUN mkdir -p /data/chat-prompts

# Kopier resten av prosjektet
COPY . .

# Sørg for at /data/chat-prompts er skrivbar for app-brukeren
RUN chmod -R 777 /data

# Eksponer port 8080 (for Fly.io)
EXPOSE 8080

# Start FastAPI med Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
