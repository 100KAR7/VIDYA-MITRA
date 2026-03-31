# Base image for backend
FROM node:14 AS backend
WORKDIR /app/backend
COPY ./backend/package*.json ./
RUN npm install
COPY ./backend ./
CMD ["npm", "start"]

# Base image for frontend
FROM node:14 AS frontend
WORKDIR /app/frontend
COPY ./frontend/package*.json ./
RUN npm install
COPY ./frontend ./
RUN npm run build

# Final stage to serve both applications
FROM nginx:alpine
COPY --from=frontend /app/frontend/build /usr/share/nginx/html
COPY --from=backend /app/backend /usr/share/nginx/html/api
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]