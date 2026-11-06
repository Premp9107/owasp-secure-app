import axios from "axios";

export const api = axios.create({
  baseURL: "/api",
  withCredentials: true,
});

function readCookie(name) {
  const parts = document.cookie ? document.cookie.split("; ") : [];
  for (const part of parts) {
    const index = part.indexOf("=");
    if (index === -1) continue;
    if (part.slice(0, index) === name) {
      return decodeURIComponent(part.slice(index + 1));
    }
  }
  return "";
}

api.interceptors.request.use((config) => {
  const method = (config.method || "get").toLowerCase();
  if (["post", "put", "patch", "delete"].includes(method)) {
    const csrf = readCookie("csrf_token");
    if (csrf) {
      config.headers["X-CSRF-Token"] = csrf;
    }
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    const url = error.config?.url || "";
    if (status === 401 && !url.includes("/auth/login") && !url.includes("/auth/register")) {
      window.dispatchEvent(new Event("vigil:unauthorized"));
    }
    return Promise.reject(error);
  }
);

export function errorMessage(error, fallback = "Request failed") {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  const errors = error?.response?.data?.errors;
  if (Array.isArray(errors) && errors.length) {
    return errors.map((item) => item.message).join(" ");
  }
  return fallback;
}
