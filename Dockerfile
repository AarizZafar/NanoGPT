FROM node:20-alpine AS frontend-builder

WORKDIR /frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1
ENV FRONTEND_DIST_DIR=/app/frontend/dist

WORKDIR /app

RUN pip install uv

COPY pyproject.toml ./
RUN uv pip install --system --index-url https://download.pytorch.org/whl/cpu "torch>=2.3.0"
RUN uv pip install --system -r pyproject.toml

COPY app/ ./app/
COPY training_data_corpus/ ./training_data_corpus/
COPY --from=frontend-builder /frontend/dist ./frontend/dist

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
