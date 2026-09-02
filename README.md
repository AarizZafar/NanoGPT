# BPE Tokenizer

A small full-stack project for exploring Byte Pair Encoding (BPE). The app lets you select a text corpus, train a tokenizer, inspect merges/vocabulary, and test encode/decode behavior from the browser.

## Tech Stack

- FastAPI backend
- React + Vite frontend
- Docker / Docker Compose
- Azure Static Web Apps + Azure Container Apps deployment branch

## Project Structure

```text
app/                  FastAPI backend
frontend/             React frontend
artifacts/            Text datasets used for tokenizer training
nginx/                Optional nginx config/docker setup
Dockerfile            Container image for the app
docker-compose.yml    Local Docker run configuration
pyproject.toml        Python project dependencies
```

## Run Locally

From the project root:

```powershell
uv sync
uv run app/main.py
```

Open:

```text
http://127.0.0.1:8001
```

## Run Frontend And Backend Separately

Backend:

```powershell
uv run app/main.py
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal, usually:

```text
http://localhost:5173
```

## Run With Docker

```powershell
docker compose up --build
```

Open:

```text
http://localhost:8001
```

## Run Tests

```powershell
python -m pytest -v
```

or, if `uv` is working correctly:

```powershell
uv run pytest -v
```

## Deployment Notes

This branch is for the Azure Static Web Apps + Azure Container Apps + Docker Hub deployment flow.

- Frontend is hosted on Azure Static Web Apps.
- Backend API runs as a Docker container on Azure Container Apps.
- Docker image is pushed to Docker Hub.
- GitHub Actions can automate image builds and frontend deployment.

