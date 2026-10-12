FROM node:22-bookworm-slim AS ui
WORKDIR /app
COPY frontend/package*.json frontend/
RUN npm ci --prefix frontend
COPY frontend frontend
RUN npm run build --prefix frontend
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend backend
COPY --from=ui /app/dist dist
RUN mkdir runtime
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh
EXPOSE 8000
CMD ["/app/docker-entrypoint.sh"]
