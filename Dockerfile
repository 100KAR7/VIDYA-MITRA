FROM node:18-alpine AS build-frontend
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

FROM python:3.9-slim
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY --from=build-frontend /app/dist ./frontend/dist
COPY app.py main.py .env.example ./

ENV PYTHONUNBUFFERED=1
ENV PORT=8080

EXPOSE 8080

CMD ["sh", "-c", "waitress-serve --host=0.0.0.0 --port=$PORT app:app"]
