# NanoGPT Training Studio

A small full-stack project for training a character-level transformer from the browser. The app lets you select a default text corpus, upload your own `.txt` file, tune hyperparameters, watch train/validation loss stream live, and inspect generated text.

## Tech Stack

- FastAPI backend
- PyTorch training pipeline
- React + Vite frontend
- Chart.js loss visualization
- Docker / Docker Compose
- Azure Static Web Apps + Azure Container Apps deployment flow

## Project Structure

```text
app/                    FastAPI backend and NanoGPT training code
frontend/               React + Vite frontend
training_data_corpus/   Default text datasets
nginx/                  Optional local nginx reverse proxy
main.py                 One-command local launcher
Dockerfile              Production container image for Azure Container Apps
docker-compose.yml      Local Docker run configuration
pyproject.toml          Python project dependencies
```

## Run Locally With One Command

Run these commands from the project root, not from inside `app/`:

```powershell
cd C:\Users\aariz.zafar\Trinity_workspace\My_workspace\nanogpt
uv sync
uv run main.py
```

What `main.py` does:

- Installs frontend packages if `frontend/node_modules` is missing.
- Builds the React frontend into `frontend/dist`.
- Starts FastAPI with Uvicorn.
- Serves the built frontend and backend API from the same local server.

Open:

```text
http://127.0.0.1:8000
```

If port `8000` is already in use, stop the old backend process or run the separate frontend/backend mode below.

## Run Frontend And Backend Separately

Use this mode while actively editing the React UI because Vite gives fast frontend refresh.

Terminal 1, from the project root:

```powershell
cd C:\Users\aariz.zafar\Trinity_workspace\My_workspace\nanogpt
uv run python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Terminal 2:

```powershell
cd C:\Users\aariz.zafar\Trinity_workspace\My_workspace\nanogpt\frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal, usually:

```text
http://localhost:5173
```

The Vite dev server proxies `/api` to `http://127.0.0.1:8000`.

## Run With Docker

```powershell
cd C:\Users\aariz.zafar\Trinity_workspace\My_workspace\nanogpt
docker compose up --build
```

Open:

```text
http://localhost
```

Docker Compose starts the FastAPI app container and an nginx reverse proxy.

## Azure / GitHub Deployment Notes

The local `main.py` launcher is only for local development. It does not change the production container startup.

When pushed to GitHub, Azure Container Apps should continue using the Dockerfile command:

```text
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The Dockerfile still builds the frontend in a Node builder stage, copies `frontend/dist` into the Python runtime image, and starts `app.main:app` on port `8000`. This keeps the Container App behavior unchanged.

For the Azure Static Web Apps + Azure Container Apps + Docker Hub flow, see:

```text
AZURE_Static_web_app_ACA_DOCKERHUB_deployment.md
```

## Cold Start Behavior

The deployed backend runs on Azure Container Apps with:

```text
min replicas = 0
max replicas = 1
```

When the backend is asleep, the frontend shows an Azure Container Apps warm-up screen while it retries `/api/datasets` and `/api/status`. Once the container wakes and default datasets load, the full training studio appears automatically.

## Useful Checks

Check whether the backend is already using port `8000`:

```powershell
netstat -ano | findstr :8000
```

Stop a process by PID:

```powershell
taskkill /PID <PID> /F
```

Build the frontend only:

```powershell
cd frontend
npm run build
```
