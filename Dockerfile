FROM python:3.11-slim

WORKDIR /app

# deps first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# app code (spec/, tests/, data/, .env excluded via .dockerignore)
COPY . .

# per-rep data + credentials live on a mounted persistent disk in prod
ENV DATA_DIR=/var/data

# hosts inject $PORT; default 8000 for local `docker run`
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
