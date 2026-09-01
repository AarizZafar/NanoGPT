

### Azure Static Web Apps + Docker Hub + Azure Container Apps Runbook

This MD document records the full deployment setup for the NanoGPT project.

```
Important 
azure_static_aca_dockerhub - this branch is created for this the specific methodology 
- Docker Hub image repository + GitHub Actions automation Azure Container Apps[backend] + Azure Static Web Apps[frontend]
```
---

## 1. Architecture

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
DOCKERHUB_USERNAME     = aarizzafar
DOCKERHUB_TOKEN        = Docker Hub access token
VITE_API_URL           = https://cae-nanogpt-prod.happyisland-c2178764.eastus.azurecontainerapps.io/api
```

Azure Static Web Apps automatically created this secret:

```text
AZURE_STATIC_WEB_APPS_API_TOKEN_GENTLE_OCEAN_01208A90F
```

This runbook does not implement automatic update `Azure Container APP`for which ```AZURE_CREDENTIALS``` are required

What this runbook implementation does - 
```text
GitHub Actions pushes the Docker image to Docker Hub.           (Till here the automation takes place).
Azure Container Apps is updated manually to pull the new image. (can update CPU/RAM for the change to take place). 
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
-> Edit and deploy (do some change in RAM/CPU).
-> confirm image: aarizzafar/nanogpt_api:latest
-> Save as a new revision
```

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
