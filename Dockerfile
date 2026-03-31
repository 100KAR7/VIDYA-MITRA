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

ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1
EXPOSE 5000

CMD ["waitress-serve", "--host=0.0.0.0", "--port=5000", "app:app"]
