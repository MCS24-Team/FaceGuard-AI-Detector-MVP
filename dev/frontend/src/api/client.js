import { API_BASE_URL } from "@/constants";

export async function fetchHealth() {
  const response = await fetch(`${API_BASE_URL}/api/health`);
  if (!response.ok) {
    throw new Error("Failed to reach backend health endpoint.");
  }
  return response.json();
}

export async function analyzeImage(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/analyze`, {
    method: "POST",
    body: formData
  });

  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || "Inference failed.");
  }
  return payload;
}

export async function signIn(credentials) {
  const response = await fetch(`${API_BASE_URL}/api/auth/signin`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(credentials)
  });

  const payload = await response.json();
  if (!response.ok) {
    const { detail } = payload;
    if (Array.isArray(detail)) {
      throw new Error(detail.map((item) => item?.msg).filter(Boolean).join("; ") || "Sign in failed.");
    }
    throw new Error(detail || "Sign in failed.");
  }
  return payload;
}

export async function signUp(credentials) {
  const response = await fetch(`${API_BASE_URL}/api/auth/signup`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(credentials)
  });

  const payload = await response.json();
  if (!response.ok) {
    const { detail } = payload;
    if (Array.isArray(detail)) {
      throw new Error(detail.map((item) => item?.msg).filter(Boolean).join("; ") || "Sign up failed.");
    }
    throw new Error(detail || "Sign up failed.");
  }
  return payload;
}

export async function googleAuth(credential) {
  const response = await fetch(`${API_BASE_URL}/api/auth/google`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ credential })
  });

  const payload = await response.json();
  if (!response.ok) {
    const { detail } = payload;
    if (Array.isArray(detail)) {
      throw new Error(detail.map((item) => item?.msg).filter(Boolean).join("; ") || "Google sign in failed.");
    }
    throw new Error(detail || "Google sign in failed.");
  }
  return payload;
}

