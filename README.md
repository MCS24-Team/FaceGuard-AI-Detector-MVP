# FaceGuard: a Privacy-Preserving AI for Detecting Deepfake Profile Photos

<p align="center">
  <img src="dev/frontend/src/assets/logo.png" alt="FaceGuard logo" width="250" />
</p>

MCS24 Team is dedicated to develop **FaceGuard: a Privacy-Preserving AI for Detecting Deepfake Profile Photos**, a user-friendly web-based system to accurately identify and classify AI-generated human face images on social media and dating platforms. **FaceGuard** is anticipated to deliver a fully functional web-based system with visual explainability via Grad-CAM heatmaps that can accurately classify profile photos as real or AI-generated. 

> **INTELLECTUAL PROPERTY NOTICE:** 
> 
> **FaceGuard** and all original materials in this repository (including source code, UI design, documentation, model integration logic and project artifacts) are intellectual property of the **MCS24 Team** unless otherwise stated.
>
> **Copyright © 2025/26 MCS24 Team. All rights reserved.**
>
> Third-party components, datasets and model weights remain the property of their respective owners and are subject to their original licenses and terms. Refer to [THIRD_PARTY_NOTICES.md](models/THIRD_PARTY_NOTICES.md) for attribution details.
> 
> If you reference this project in reports, demos or derivative works, please credit it as:
> ```
> FaceGuard: a Privacy-Preserving AI for Detecting Deepfake Profile Photos, MCS24 Team, 2026.
> ```
>
> **DISCLAIMER:** This project is for educational and research purposes only. It is not intended for commercial use and is not endorsed by any organization or entity. Use at your own risk.

## Project Overview

The FaceGuard MVP provides:

- Web-based image upload and preview workflow
- Backend inference API for binary REAL/FAKE classification
- Confidence score and model metadata in responses
- In-memory processing with no database persistence
- Account authentication and authorisation
- Explainability overlays (Grad-CAM heatmaps)

![FaceGuard result panel sample](result_panel.png)

## Repository Structure

```text
FaceGuard-AI-Detector/
├── config/
│   └── settings.py
│
├── dev/
│   ├── backend/
│   └── frontend/
│
├── docs/
│   ├── design/
│   ├── diagrams/
│   └── documents/
│
└── models/
  ├── pretrained/
  │   ├── vit.pth
  │   ├── xception.pth
  │   └── pg_fdd.pth
  │
  ├── README.md
  └── THIRD_PARTY_NOTICES.md
```

## Prerequisites

- Python 3.9+
- Node.js 18+
- npm 9+
- A compatible model checkpoint file (eg. `models/pretrained/vit.pth`)

## Quick Start

### 1. Install Python dependencies

From the repository root:

```bash
python -m venv .venv
```

Activate the virtual environment:

```bash
# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

Install backend dependencies:

```bash
pip install -r requirements.txt
```

### 2. Install frontend dependencies

```bash
cd dev/frontend
npm install
```

### 3. Start backend

In a terminal from the repository root:

```bash
cd dev/backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 4. Start frontend

In a second terminal:

```bash
cd dev/frontend
npm run dev
```

Open the application at:

- `http://localhost:5173`

## Health Endpoint

Verify backend readiness:

- `GET http://127.0.0.1:8000/api/health`

Example response:

```json
{
  "status": "ok",
  "model_ready": true,
  "model_name": "vit"
}
```

If `model_ready` is `false`, the backend is reachable but the configured
checkpoint file is missing or failed to load.

## API Contract

### GET /api/health

Returns service and model availability status.

### POST /api/analyze

Accepts `multipart/form-data` with field:

- `file` (JPEG, PNG, or WebP)

Example response:

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

## Model Checkpoints

The backend loads model checkpoints from a local path or from Hugging Face Hub
based on environment variables and `config/settings.py`.

Common checkpoint names:

- `vit.pth`
- `vit3.pth`
- `xception.pth`
- `pg_fdd.pth`

Large model binaries are excluded from source control. Keep checkpoints in local
or approved storage and distribute them according to license terms.

### Hugging Face Hub on Render

For deployment, upload the checkpoint to a Hugging Face model repository and set
these Render backend environment variables:

```text
HF_MODEL_REPO=your-username/faceguard-vit3
HF_MODEL_FILE=vit3.pth
HF_TOKEN=your_hugging_face_read_token
MODEL_CACHE_DIR=/tmp/faceguard_models
FACEGUARD_MODEL_NAME=vit
FACEGUARD_FRONTEND_ORIGINS=https://your-vercel-app.vercel.app
```

If you want to keep local development using a file on disk, set:

```text
FACEGUARD_MODEL_PATH=models/baseline/vit3.pth
```

## Design and Project Artifacts

Supporting design and project materials are available in:

- `docs/design/`
- `docs/diagrams/`
- `docs/documents/`

## Additional Documentation

For development operations and troubleshooting guidance, refer to [**Developer Guide**](DEVELOPER_GUIDE.md).


