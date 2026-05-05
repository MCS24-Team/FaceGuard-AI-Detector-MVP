# FaceGuard MVP Developer Guide

This guide defines the standard local development workflow for FaceGuard.
It is intended for contributors, maintainers, and project evaluators.

## 1. Service Topology and Local Ports

FaceGuard runs as two independent local services:

| Service | Responsibility | Default URL |
|---|---|---|
| Backend (FastAPI) | Model loading, inference, API endpoints | `http://127.0.0.1:8000` |
| Frontend (React + Vite) | User interface and API client | `http://localhost:5173` |

Both services must run concurrently during local development.

Important:

- Open only `http://localhost:5173` in your browser for normal use.
- The frontend communicates with the backend on port 8000.
- Localhost and 127.0.0.1 addresses are local loopback addresses and are not sensitive.

## 2. Prerequisites

- Python 3.9 or later
- Node.js 18 or later
- npm 9 or later
- A valid model checkpoint in `models/pretrained/` (for example, `vit.pth`)

## 3. Initial Setup

### 3.1 Python environment and dependencies

From the repository root:

```powershell
python -m venv .venv
```

Activate environment:

```powershell
# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

### 3.2 Frontend dependencies

```powershell
cd dev/frontend
npm install
```

## 4. Standard Startup Procedure

Two terminals are required.

### Terminal 1: Start backend

```powershell
cd dev/backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Expected output includes:

```text
Uvicorn running on http://127.0.0.1:8000
```

### Terminal 2: Start frontend

```powershell
cd dev/frontend
npm run dev
```

Expected output includes:

```text
Local: http://localhost:5173/
```

If Vite reports that 5173 is in use, stop the existing process rather than
running on another port, because backend CORS policy may be restricted to 5173.

## 5. Runtime Verification

Verify backend health:

- `http://127.0.0.1:8000/api/health`

Expected JSON:

```json
{
  "status": "ok",
  "model_ready": true,
  "model_name": "vit"
}
```

If `model_ready` is `false`, confirm that the configured checkpoint exists in
`models/pretrained/` and can be loaded.

## 6. Model Switching Procedure

Model selection is controlled by environment variables and `config/settings.py`.

Typical configuration values:

```python
model_name: str = "vit"
model_path: Path = REPO_ROOT / "models" / "baseline" / "vit3.pth"
```

Environment overrides:

```powershell
$env:FACEGUARD_MODEL_NAME="vit"
$env:FACEGUARD_MODEL_PATH="models/baseline/vit3.pth"
```

For Render deployments that download the checkpoint from Hugging Face Hub:

```text
HF_MODEL_REPO=your-username/faceguard-vit3
HF_MODEL_FILE=vit3.pth
HF_TOKEN=your_hugging_face_read_token
MODEL_CACHE_DIR=/tmp/faceguard_models
FACEGUARD_MODEL_NAME=vit
FACEGUARD_FRONTEND_ORIGINS=https://your-vercel-app.vercel.app
```

For Vercel frontend deployments, set:

```text
VITE_API_BASE_URL=https://your-render-backend.onrender.com
```

After editing model settings:

1. Stop backend (`Ctrl+C`).
2. Remove Python bytecode caches.
3. Restart backend.
4. Re-check `/api/health` and verify `model_name`.

Bytecache cleanup command:

```powershell
Get-ChildItem -Path . -Recurse -Directory -Filter "__pycache__" |
    Remove-Item -Recurse -Force
```

## 7. Restart Matrix

| Change Type | Required Action |
|---|---|
| File change under `dev/backend/` | Usually auto-reloads with `--reload` |
| Change in `config/settings.py` | Manually restart backend |
| File change under `dev/frontend/src/` | Hot reload handles update |
| Change in `dev/frontend/package.json` | Run `npm install`, restart frontend |
| Change in `requirements.txt` | Reinstall Python deps, restart backend |

## 8. Troubleshooting Runbook

### 8.1 Backend appears stale after config change

Symptoms:

- `/api/health` returns outdated model metadata
- Behavior does not match latest `settings.py`

Resolution:

1. Stop backend process.
2. Delete all `__pycache__` directories.
3. Restart backend and verify `/api/health`.

### 8.2 Port 8000 already in use

```powershell
$p = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue |
     Select-Object -First 1 -ExpandProperty OwningProcess
if ($p) { Stop-Process -Id $p -Force; Write-Output "Stopped PID $p" }
else { Write-Output "Port 8000 is free" }
```

### 8.3 Port 5173 already in use

```powershell
$p = Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue |
     Select-Object -First 1 -ExpandProperty OwningProcess
if ($p) { Stop-Process -Id $p -Force; Write-Output "Stopped PID $p" }
else { Write-Output "Port 5173 is free" }
```

### 8.4 Browser shows CORS or Failed to fetch

Checklist:

1. Confirm backend is running.
2. Confirm frontend is running on `http://localhost:5173`.
3. Confirm health endpoint returns a valid response.

### 8.5 Full clean restart (last resort)

```powershell
# Stop Python and Node processes
Get-Process -Name python -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process -Name node -ErrorAction SilentlyContinue | Stop-Process -Force

# Clear bytecache
Get-ChildItem -Path . -Recurse -Directory -Filter "__pycache__" |
    Remove-Item -Recurse -Force

# Restart services
cd dev/backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# In a separate terminal
cd dev/frontend
npm run dev
```

## 9. API Reference

### GET /api/health

Returns backend availability and model load status.

### POST /api/analyze

Accepts image upload in `multipart/form-data` using field name `file`.

Supported formats:

- JPEG
- PNG
- WebP

Typical response:

```json
{
  "label": "FAKE",
  "confidence": 0.9123,
  "fake_probability": 0.9123,
  "threshold": 0.5,
  "explanation": "Prediction is based on a ViT deepfake classifier...",
  "model_name": "vit",
  "heatmap_overlay": "data:image/png;base64,...",
  "explainability_method": "grad_cam"
}
```

## 10. Contributor Notes

- Keep documentation aligned with actual commands and directory paths.
- Avoid committing local secrets, private environment files, or binary artifacts not intended for distribution.
- Update this guide when setup, ports, or model-selection flow changes.
