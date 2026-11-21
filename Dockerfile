# ARGUS-AI Python app
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY argus/ argus/
COPY argus_manifest.json .
COPY data/ data/

EXPOSE 8077
# Store DB lives on a volume in compose so data survives restarts.
CMD ["python", "-m", "argus.cli", "--db", "/data/argus.db", "serve", "--port", "8077"]
