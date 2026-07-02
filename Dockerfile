FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PORT=8080

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py main.py README.md .env.example ./
COPY backend ./backend
COPY config ./config
COPY data ./data
COPY frontend ./frontend
COPY inference ./inference
COPY models ./models
COPY preprocessing ./preprocessing
COPY training ./training
COPY utils ./utils

RUN mkdir -p logs outputs/plots outputs/predictions outputs/reports

EXPOSE 8080

CMD ["sh", "-c", "waitress-serve --host=0.0.0.0 --port=${PORT:-8080} app:app"]
