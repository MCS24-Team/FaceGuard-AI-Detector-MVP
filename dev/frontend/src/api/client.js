import { API_BASE_URL } from "@/constants";

async function readPayload(response, fallbackMessage) {
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return response.json();
  }

  const text = await response.text();
  return {
    detail: text || fallbackMessage
  };
}

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

  const payload = await readPayload(response, "Inference failed.");
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

  const payload = await readPayload(response, "Sign in failed.");
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

  const payload = await readPayload(response, "Sign up failed.");
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

  const payload = await readPayload(response, "Google sign in failed.");
  if (!response.ok) {
    const { detail } = payload;
    if (Array.isArray(detail)) {
      throw new Error(detail.map((item) => item?.msg).filter(Boolean).join("; ") || "Google sign in failed.");
    }
    throw new Error(detail || "Google sign in failed.");
  }
  return payload;
}

