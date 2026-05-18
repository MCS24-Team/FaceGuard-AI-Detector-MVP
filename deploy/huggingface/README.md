---
title: FaceGuard API
emoji: 🛡️
colorFrom: teal
colorTo: blue
sdk: docker
pinned: false
---

# FaceGuard API

FastAPI backend for the FaceGuard AI Detector MVP.

This Space runs the backend API used by the Vercel frontend. It loads the configured deepfake detection model from Hugging Face Hub and exposes endpoints such as `/api/health`, `/api/analyze`, `/api/auth/signin`, and `/api/profile`.
