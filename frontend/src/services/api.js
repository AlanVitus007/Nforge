import axios from "axios";

const resolveBaseUrl = () => {
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