import axios from "axios";

const resolveBaseUrl = () => {
    // If running in browser, dynamically bind to the current host on port 8000
    // so localhost always calls localhost, and LAN access automatically uses the LAN host
    if (typeof window !== "undefined" && window.location && window.location.hostname) {
        const host = window.location.hostname;
        return `http://${host}:8000/api`;
    }

    const rawUrl = import.meta.env.VITE_API_URL || "http://localhost:8000/api";
    const trimmed = rawUrl.trim().replace(/\/+$/, "");
    if (trimmed.endsWith("/api")) {
        return trimmed;
    }
    return `${trimmed}/api`;
};

const api = axios.create({
    baseURL: resolveBaseUrl(),
});

api.interceptors.request.use((config) => {
    const token = localStorage.getItem("token");

    if (token) {
        config.headers.Authorization = `Token ${token}`;
    }

    return config;
});

export default api;