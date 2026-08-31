# Azure Static Web Apps + Docker Hub + Azure Container Apps Runbook

This document records the full deployment setup for the NanoGPT project.

It covers:

- Git branch strategy
- Docker Hub image repository
- GitHub Actions automation
- Azure Container Apps backend
- Azure Static Web Apps frontend
- React/Vite frontend migration
- Environment variables and secrets
- Manual Container App revision updates
- Refresh/reconnect behavior
- Common errors faced and fixes
- Cost-control notes for revisions, replicas, and logging

---

## 1. Final Architecture

```text
Developer pushes code to GitHub
        |
        +--> GitHub Actions builds Docker image
        |       |
        |       +--> Docker image is pushed to Docker Hub
        |               |
        |               +--> Azure Container Apps runs backend container
        |
        +--> Azure Static Web Apps builds React frontend
                |
                +--> Frontend calls backend through VITE_API_URL
```

Services used:

```text
Frontend hosting: Azure Static Web Apps Free / Hobby
Backend hosting: Azure Container Apps
Image registry: Docker Hub
Source control: GitHub
Automation: GitHub Actions
Backend framework: FastAPI + Uvicorn
Frontend framework: React + Vite
ML runtime: PyTorch CPU
```

Important URLs:

```text
NanoGPT Static Web App frontend:
https://gentle-ocean-01208a90f.7.azurestaticapps.net/

NanoGPT Container Apps backend:
https://cae-nanogpt-prod.happyisland-c2178764.eastus.azurecontainerapps.io

Backend API base URL:
https://cae-nanogpt-prod.happyisland-c2178764.eastus.azurecontainerapps.io/api

Health check:
https://cae-nanogpt-prod.happyisland-c2178764.eastus.azurecontainerapps.io/api/health
```

Expected health response:

```json
{
  "status": "ok",
  "training": false,
  "has_model": false,
  "has_text": false
}
```

---

## 2. Branch Strategy

The original VM/Jenkins-style deployment can stay on `main`.

For this deployment approach, use a separate branch:

```text
azure_static_aca_dockerhub
```

Create and push it:

```bash
git checkout main
git pull origin main
git checkout -b azure_static_aca_dockerhub
git push -u origin azure_static_aca_dockerhub
```

Why this branch exists:

```text
main = existing Azure VM + Jenkins deployment path
azure_static_aca_dockerhub = Static Web Apps + Docker Hub + Container Apps deployment
```

This keeps both deployment styles available for learning, rollback, and comparison.

---

## 3. Docker Hub Setup

Docker Hub repository:

```text
aarizzafar/nanogpt_api
```

Docker Hub access token:

```text
Token name: NanoGPT
Purpose: GitHub Actions pushes Docker images to Docker Hub
```

Creating a Docker Hub personal access token does not create a charge by itself.

Cost caution:

```text
Docker Hub can apply limits or charges based on plan, storage, transfer, and pull usage.
For this small project and normal GitHub Actions usage, the token itself is not the cost driver.
```

---

## 4. GitHub Secrets

Go to the GitHub repository:

```text
Settings
-> Secrets and variables
-> Actions
-> Secrets
-> New repository secret
```

Add these repository secrets:

```text
DOCKERHUB_USERNAME = aarizzafar
DOCKERHUB_TOKEN = Docker Hub access token
VITE_API_URL = https://cae-nanogpt-prod.happyisland-c2178764.eastus.azurecontainerapps.io/api
```

Azure Static Web Apps automatically created this secret:

```text
AZURE_STATIC_WEB_APPS_API_TOKEN_GENTLE_OCEAN_01208A90F
```

Not used in this runbook style:

```text
AZURE_CREDENTIALS
```

Reason:

```text
This deployment follows the same style as the BPE Tokenizer project.
GitHub Actions pushes the Docker image to Docker Hub.
Azure Container Apps is updated manually to pull the new image.
```

`AZURE_CREDENTIALS` is only needed if you want a future workflow step that automatically runs:

```bash
az containerapp update ...
```

---

## 5. Docker Hub GitHub Action

Workflow file:

```text
.github/workflows/dockerhub-deploy.yml
```

Purpose:

```text
Whenever code is pushed to azure_static_aca_dockerhub,
GitHub Actions builds the Docker image and pushes it to Docker Hub.
```

Workflow:

```yaml
name: Build and push Docker Image

on:
  push:
    branches:
      - azure_static_aca_dockerhub

jobs:
  docker-build-push:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Login to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}

      - name: Build and push image
        uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: |
            aarizzafar/nanogpt_api:latest
            aarizzafar/nanogpt_api:${{ github.sha }}
```

After a successful run, Docker Hub should show tags:

```text
latest
<commit-sha>
```

---

## 6. React/Vite Frontend Migration

Original issue:

```text
The old frontend was one plain frontend/index.html file.
It used relative API calls like /api/datasets and /api/train.
```

That worked when FastAPI served both frontend and backend from the same Container App URL.

It did not match the Static Web Apps pattern because:

```text
Static Web App URL: https://gentle-ocean-01208a90f.7.azurestaticapps.net
Backend URL:        https://cae-nanogpt-prod.happyisland-c2178764.eastus.azurecontainerapps.io
```

If the frontend kept calling `/api`, the browser would call:

```text
https://gentle-ocean-01208a90f.7.azurestaticapps.net/api/...
```

That is wrong because Static Web Apps does not host this FastAPI backend.

Fix:

```text
Replace the single HTML frontend with a Vite React app.
Use VITE_API_URL for production backend calls.
Fallback to /api for local same-origin development.
```

Important frontend files:

```text
frontend/index.html
frontend/package.json
frontend/package-lock.json
frontend/vite.config.js
frontend/.nvmrc
frontend/src/api.js
frontend/src/main.jsx
frontend/src/styles.css
```

---

## 7. Frontend API Code

File:

```text
frontend/src/api.js
```

Important setup:

```js
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

function joinUrl(baseUrl, path) {
  const cleanBase = baseUrl.replace(/\/$/, '');
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${cleanBase}${cleanPath}`;
}

export function apiUrl(path) {
  return joinUrl(API_BASE_URL, path);
}

export function websocketUrl(path) {
  if (API_BASE_URL.startsWith('http')) {
    const url = new URL(apiUrl(path));
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
    return url.toString();
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}${apiUrl(path)}`;
}
```

Meaning:

```text
Local Vite dev server:
VITE_API_URL not set -> frontend calls /api
Vite proxy forwards /api to FastAPI on localhost:8000

Azure Static Web Apps:
VITE_API_URL set -> frontend calls Container Apps backend

Container App root URL:
FastAPI serves frontend/dist and /api is same-origin
```

---

## 8. Local Frontend Development

Start backend:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Start frontend:

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

Local Vite proxy:

```js
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
});
```

---

## 9. Dockerfile Purpose

The Dockerfile builds one deployable container image containing:

```text
1. React/Vite frontend build output
2. FastAPI backend
3. Training datasets
4. CPU-only PyTorch runtime
```

Dockerfile:

```dockerfile
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
```

Why CPU-only PyTorch is installed:

```text
Azure Container Apps was configured with 0.5 CPU and 1 Gi memory.
GPU/CUDA wheels are large and slow to install.
The app is intended to run on CPU for this deployment.
```

---

## 10. Backend Static File Serving

File:

```text
app/main.py
```

FastAPI serves the built React app from:

```text
frontend/dist
```

Container environment variable:

```text
FRONTEND_DIST_DIR=/app/frontend/dist
```

Important behavior:

```text
/api/*        = FastAPI API routes
/assets/*     = Vite static assets
/*            = React app fallback
```

This is why the Container App URL can also show the UI:

```text
https://cae-nanogpt-prod.happyisland-c2178764.eastus.azurecontainerapps.io/
```

But the final public frontend is the Static Web App URL:

```text
https://gentle-ocean-01208a90f.7.azurestaticapps.net/
```

---

## 11. CORS Setup

Because Static Web Apps and Container Apps use different domains, the backend needs CORS.

Allowed origins include:

```text
http://localhost
http://localhost:5173
http://localhost:8000
http://127.0.0.1:5173
http://127.0.0.1:8000
https://cae-nanogpt-prod.happyisland-c2178764.eastus.azurecontainerapps.io
https://*.azurestaticapps.net
```

This allows the React frontend on Static Web Apps to call the FastAPI backend on Container Apps.

---

## 12. Azure Container Apps Setup

Resource group:

```text
rg_NanoGPT_prod
```

Container Apps environment:

```text
cae-nanogpt-env
```

Container App:

```text
cae-nanogpt-prod
```

Container App URL:

```text
https://cae-nanogpt-prod.happyisland-c2178764.eastus.azurecontainerapps.io
```

Container image:

```text
docker.io/aarizzafar/nanogpt_api:latest
```

Container settings:

```text
Command override: empty
Arguments override: empty
```

Reason:

```text
The Dockerfile already contains the startup CMD.
Azure Container Apps should use the Dockerfile command.
```

Resource allocation used:

```text
CPU: 0.5
Memory: 1 Gi
```

Ingress settings:

```text
Ingress: Enabled
Accept traffic from anywhere: Yes
Target port: 8000
Transport: Auto
```

Scale settings for cost control:

```text
Min replicas: 0
Max replicas: 1
Revision mode: Single
```

Why max replicas should be 1:

```text
NanoGPT stores model, tokenizer, training flag, loss history, and generated text in memory.
Multiple replicas would not share that state.
```

---

## 13. Manual Container App Image Refresh

With the current runbook style:

```text
GitHub Actions pushes Docker image to Docker Hub.
Azure Container Apps does not automatically pull the new :latest image.
```

To make Azure run the latest image, create a new revision manually:

```text
Azure Portal
-> Container Apps
-> cae-nanogpt-prod
-> Application
-> Containers
-> Edit and deploy
-> confirm image: aarizzafar/nanogpt_api:latest
-> Save as a new revision
```

This is not creating a second permanent paid app.

Cost note:

```text
Container Apps charges mainly for running replicas.
Inactive revisions are retained as history.
In single-revision mode, traffic moves to the new revision and the old revision becomes inactive.
There can be a brief overlap during deployment, but it is not a long-term duplicate app.
```

Use this manual refresh after backend or Docker image changes.

You do not need this for frontend-only changes once Static Web Apps is active.

---

## 14. Azure Static Web Apps Setup

Static Web App:

```text
gentle-ocean-01208a90f
```

Static Web App URL:

```text
https://gentle-ocean-01208a90f.7.azurestaticapps.net/
```

Settings used:

```text
Resource group: rg_NanoGPT_prod
Plan: Free / Hobby
Source: GitHub
Repository: NanoGPT
Branch: azure_static_aca_dockerhub
Build preset: React
App location: frontend
API location: empty
Output location: dist
```

Deployment authorization policy:

```text
GitHub
```

Reason:

```text
GitHub authorization lets Azure create/use GitHub Actions for automatic frontend deployments.
```

---

## 15. Static Web Apps Workflow

Azure created this workflow:

```text
.github/workflows/azure-static-web-apps-gentle-ocean-01208a90f.yml
```

Important build/deploy step:

```yaml
- name: Build And Deploy
  id: builddeploy
  uses: Azure/static-web-apps-deploy@v1
  env:
    VITE_API_URL: ${{ secrets.VITE_API_URL }}
  with:
    azure_static_web_apps_api_token: ${{ secrets.AZURE_STATIC_WEB_APPS_API_TOKEN_GENTLE_OCEAN_01208A90F }}
    repo_token: ${{ secrets.GITHUB_TOKEN }}
    action: "upload"
    app_location: "./frontend"
    api_location: ""
    output_location: "dist"
```

Why `VITE_API_URL` must be in the workflow:

```text
Vite reads VITE_API_URL at build time.
If the workflow does not pass the secret into the build environment,
the frontend falls back to /api and calls the wrong host.
```

---

## 16. Rebase After Azure Creates Workflow

When Azure Static Web Apps is created from the portal, Azure may commit a workflow file directly to GitHub.

That means local code can become behind remote.

Before editing the Azure workflow locally, run:

```bash
git switch azure_static_aca_dockerhub
git pull --rebase origin azure_static_aca_dockerhub
```

Then inspect workflows:

```bash
dir .github\workflows
```

Expected workflow files:

```text
dockerhub-deploy.yml
azure-static-web-apps-gentle-ocean-01208a90f.yml
```

After editing the Static Web Apps workflow, commit and push:

```bash
git add .github/workflows/azure-static-web-apps-gentle-ocean-01208a90f.yml
git commit -m "Pass API URL to Static Web Apps build"
git push origin azure_static_aca_dockerhub
```

---

## 17. Static Web Apps Environment Variable

GitHub Actions secret:

```text
VITE_API_URL = https://cae-nanogpt-prod.happyisland-c2178764.eastus.azurecontainerapps.io/api
```

Important:

```text
This value must be available during the Static Web Apps build.
Changing the secret requires a new frontend deployment.
```

Trigger a new deployment:

```bash
git commit --allow-empty -m "Redeploy Static Web App"
git push origin azure_static_aca_dockerhub
```

---

## 18. Verifying The Final Deployment

Open frontend:

```text
https://gentle-ocean-01208a90f.7.azurestaticapps.net/
```

Expected UI behavior:

```text
Default datasets load.
Selecting a dataset shows vocab size.
Start Training begins a backend training job.
Loss chart updates.
Loss log receives entries.
Generated text appears.
Refreshing the page during training restores state and reconnects to stream.
```

Direct backend checks:

```text
https://cae-nanogpt-prod.happyisland-c2178764.eastus.azurecontainerapps.io/api/health
https://cae-nanogpt-prod.happyisland-c2178764.eastus.azurecontainerapps.io/api/status
https://cae-nanogpt-prod.happyisland-c2178764.eastus.azurecontainerapps.io/api/datasets
```

Expected `/api/status` shape:

```json
{
  "training": false,
  "has_model": false,
  "has_text": false,
  "vocab_size": null,
  "dataset_name": null,
  "loss_history": [],
  "generated_text": "",
  "train_config": {}
}
```

Browser DevTools check:

```text
F12
-> Network
-> datasets request
```

Correct request:

```text
https://cae-nanogpt-prod.happyisland-c2178764.eastus.azurecontainerapps.io/api/datasets
```

Wrong request:

```text
https://gentle-ocean-01208a90f.7.azurestaticapps.net/api/datasets
```

---

## 19. Error: `/api/health` Returned Not Found

Observed:

```json
{"detail":"Not Found"}
```

Cause:

```text
The code had /api/health locally, but Azure Container Apps was still running an old image/revision.
Docker Hub had the new image, but Container Apps had not pulled it yet.
```

Fix:

```text
Create a new Container Apps revision using the latest Docker Hub image.
```

Portal path:

```text
Container Apps
-> cae-nanogpt-prod
-> Application
-> Containers
-> Edit and deploy
-> Save as a new revision
```

Expected after fix:

```json
{"status":"ok","training":false,"has_model":false,"has_text":false}
```

---

## 20. Error: Frontend Called Wrong `/api`

Observed:

```text
Dataset list does not load.
Frontend shows failed request / 404.
```

Cause:

```text
The frontend was calling /api on the Static Web Apps domain.
Static Web Apps was not hosting the FastAPI backend.
```

Wrong:

```text
https://gentle-ocean-01208a90f.7.azurestaticapps.net/api/datasets
```

Correct:

```text
https://cae-nanogpt-prod.happyisland-c2178764.eastus.azurecontainerapps.io/api/datasets
```

Fix:

```text
Use a Vite React frontend with VITE_API_URL.
Add VITE_API_URL to GitHub Actions secrets.
Pass VITE_API_URL into the Azure Static Web Apps workflow.
```

---

## 21. Error: `Training stream disconnected`

Observed:

```text
Training stream disconnected
```

Cause:

```text
The React frontend opened the WebSocket before or around the same time as starting training.
If the socket closed or hiccuped, the UI showed a hard error immediately.
```

Verification:

```text
Direct WebSocket connection to the Container App worked.
That meant Azure ingress was not the main problem.
```

Fix:

```text
Start training first.
Then connect WebSocket.
Retry the stream connection up to 3 times.
Do not show an error for a normal training-complete socket close.
```

Relevant frontend behavior:

```text
connectTrainingStream()
startTraining()
socketRef
```

---

## 22. Error: Refresh During Training Shows `Training already running`

Observed:

```text
User starts training.
User refreshes the browser.
Frontend state resets.
Backend is still training.
User clicks Start Training again.
Backend returns: Training already running.
```

Cause:

```text
The backend training state lived in memory.
The browser state disappeared on refresh.
The old frontend did not reload the backend training state.
```

Fix:

Backend now stores:

```text
dataset_name
loss_history
generated_text
train_config
training
vocab_size
```

Frontend now:

```text
Calls /api/status on page load.
Restores selected dataset and vocab size.
Restores loss chart and loss log.
Restores generated text.
Reconnects to WebSocket if training is still running.
Recovers from "Training already running" by reloading /api/status.
```

Limit:

```text
This survives browser refresh.
It does not survive Container App restart or scale-to-zero.
State is still in backend memory, not a database.
```

---

## 23. Error: Torch Install Took Too Long / Pulled GPU Packages

Observed:

```text
Docker build/install was slow.
Large CUDA/GPU-related PyTorch packages appeared unnecessary.
```

Cause:

```text
Default torch install can pull large builds.
This deployment runs on CPU-only Azure Container Apps.
```

Fix:

```dockerfile
RUN uv pip install --system --index-url https://download.pytorch.org/whl/cpu "torch>=2.3.0"
RUN uv pip install --system -r pyproject.toml
```

Resource settings:

```text
CPU: 0.5
Memory: 1 Gi
```

Training note:

```text
This is fine for demos and small runs.
Training will be slower than GPU or larger CPU allocations.
Use smaller hyperparameters for smoother demos.
```

---

## 24. Error: React Build Failed With Missing `Github` Export

Observed during local build:

```text
"Github" is not exported by lucide-react
```

Cause:

```text
The installed lucide-react package version did not export a GitHub brand icon named Github.
```

Fix:

```text
Use a generic lucide icon instead.
The UI uses Code2 for the repository link.
```

Validation:

```bash
cd frontend
npm run build
```

Expected:

```text
vite build completes successfully
```

---

## 25. Error: Local `python` Command Blocked By pyenv

Observed:

```text
No global/local python version has been set yet.
Please set the global/local version by typing:
pyenv global 3.7.4
pyenv local 3.7.4
```

Cause:

```text
The global python shim was controlled by pyenv and did not have a selected version.
```

Fix:

```powershell
.\.venv\Scripts\python.exe -m compileall app
```

This uses the project virtual environment directly.

---

## 26. Error: Docker Build Could Not Run Locally

Observed:

```text
failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine
```

Cause:

```text
Docker Desktop / Docker daemon was not running locally.
```

Fix:

```text
Start Docker Desktop, then rerun docker build.
```

Optional local validation:

```bash
docker build -t nanogpt-react-test .
docker run --rm -p 8000:8000 nanogpt-react-test
```

Then open:

```text
http://localhost:8000
http://localhost:8000/api/health
```

---

## 27. Error: Need To Rebase After Azure Adds Workflow

Observed:

```text
Azure Static Web Apps created a workflow on GitHub.
Local branch did not have that file yet.
```

Cause:

```text
Azure committed directly to the remote branch.
Local branch was behind remote.
```

Fix:

```bash
git switch azure_static_aca_dockerhub
git pull --rebase origin azure_static_aca_dockerhub
```

Then edit:

```text
.github/workflows/azure-static-web-apps-gentle-ocean-01208a90f.yml
```

Add:

```yaml
env:
  VITE_API_URL: ${{ secrets.VITE_API_URL }}
```

Commit and push.

---

## 28. Log Analytics And Cost Control

Resources seen in the resource group:

```text
cae-nanogpt-env
cae-nanogpt-prod
workspacergnanogptprod96ec
```

The workspace is a Log Analytics workspace.

Disabling Container Apps logs:

```text
Azure Portal
-> Resource group: rg_NanoGPT_prod
-> cae-nanogpt-env
-> Monitoring
-> Logging options
-> Logs destination: Don't save logs
-> Save
```

CLI option:

```bash
az containerapp env update \
  --name cae-nanogpt-env \
  --resource-group rg_NanoGPT_prod \
  --logs-destination none
```

After logs are disabled, the workspace can be deleted only if nothing else uses it:

```text
Resource group: rg_NanoGPT_prod
-> workspacergnanogptprod96ec
-> Delete
```

Important:

```text
The workspace existing is not usually the main cost.
Log ingestion and retention are the cost drivers.
Disable logs first, then delete the workspace if it is unused.
```

---

## 29. Current Project Files That Matter

Backend:

```text
app/main.py
app/api/routes.py
app/api/websocket.py
app/state.py
app/core/model.py
app/core/trainer.py
app/core/generator.py
app/core/layers.py
app/core/embeddings.py
app/utils/tokenizer.py
app/schemas/train_schema.py
```

Frontend:

```text
frontend/index.html
frontend/package.json
frontend/package-lock.json
frontend/vite.config.js
frontend/.nvmrc
frontend/src/api.js
frontend/src/main.jsx
frontend/src/styles.css
```

Deployment:

```text
Dockerfile
docker-compose.yml
nginx/nginx.conf
.github/workflows/dockerhub-deploy.yml
.github/workflows/azure-static-web-apps-gentle-ocean-01208a90f.yml
```

Data:

```text
training_data_corpus/law_of_human_nature.txt
training_data_corpus/rich_dad_poor_dad.txt
training_data_corpus/shakes_spear.txt
```

---

## 30. Normal Deployment Workflow From Now On

For frontend-only changes:

```bash
git add frontend
git commit -m "Update frontend"
git push origin azure_static_aca_dockerhub
```

Result:

```text
Azure Static Web Apps workflow runs.
Frontend redeploys automatically.
No Container App manual refresh needed.
```

For backend, Dockerfile, dependency, or dataset changes:

```bash
git add .
git commit -m "Update backend"
git push origin azure_static_aca_dockerhub
```

Result:

```text
Docker Hub workflow builds and pushes aarizzafar/nanogpt_api:latest.
Then manually create a new Container App revision to pull the latest image.
```

Manual backend refresh:

```text
Azure Portal
-> Container Apps
-> cae-nanogpt-prod
-> Application
-> Containers
-> Edit and deploy
-> Save as a new revision
```

Then verify:

```text
https://cae-nanogpt-prod.happyisland-c2178764.eastus.azurecontainerapps.io/api/health
https://gentle-ocean-01208a90f.7.azurestaticapps.net/
```

---

## 31. Future Automation Goal

Current automation:

```text
Push code
-> Docker image builds and pushes to Docker Hub
-> Static Web App rebuilds and deploys frontend
```

Manual step that still exists:

```text
Azure Container Apps must be updated manually to pull the new Docker image.
```

Future improvement:

```text
After Docker Hub image push, automatically update Azure Container App revision.
```

This would require GitHub secrets:

```text
AZURE_CREDENTIALS
AZURE_RESOURCE_GROUP
AZURE_CONTAINER_APP_NAME
```

Example future workflow step:

```yaml
- name: Login to Azure
  uses: azure/login@v3
  with:
    creds: ${{ secrets.AZURE_CREDENTIALS }}

- name: Update Azure Container App
  uses: azure/cli@v2
  with:
    inlineScript: |
      az containerapp update \
        --name cae-nanogpt-prod \
        --resource-group rg_NanoGPT_prod \
        --image docker.io/aarizzafar/nanogpt_api:${{ github.sha }}
```

This was intentionally not used in the final current setup because the goal was to match the BPE Tokenizer runbook style.

---

## 32. Important Names Used

```text
GitHub repository:
AarizZafar/NanoGPT

GitHub branch:
azure_static_aca_dockerhub

Docker Hub repository:
aarizzafar/nanogpt_api

Resource group:
rg_NanoGPT_prod

Azure Container Apps environment:
cae-nanogpt-env

Azure Container App:
cae-nanogpt-prod

Azure Container App URL:
https://cae-nanogpt-prod.happyisland-c2178764.eastus.azurecontainerapps.io

Azure Static Web App:
gentle-ocean-01208a90f

Azure Static Web App URL:
https://gentle-ocean-01208a90f.7.azurestaticapps.net/

Frontend API URL:
https://cae-nanogpt-prod.happyisland-c2178764.eastus.azurecontainerapps.io/api

Docker image:
docker.io/aarizzafar/nanogpt_api:latest
```

---

## 33. Final Verification Checklist

Use this checklist after any deployment:

```text
[ ] GitHub Actions Docker workflow passed.
[ ] Docker Hub latest tag updated.
[ ] If backend changed, Container App new revision was created.
[ ] /api/health returns status ok.
[ ] Static Web Apps workflow passed.
[ ] Static Web App URL loads React UI.
[ ] Dataset list appears.
[ ] Network tab shows API calls going to Container Apps backend.
[ ] Training starts.
[ ] Loss chart updates.
[ ] Generated text appears.
[ ] Browser refresh during training restores/reconnects.
```

