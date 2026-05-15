import appConfig from "../../../config/frontend_settings.json";

export const APP_CONFIG = appConfig;
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
export const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || "";
export const USER_EMAIL_STORAGE_KEY = "faceguard:userEmail";
