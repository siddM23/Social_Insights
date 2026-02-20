export const API_URL = (typeof window !== 'undefined' && window.location.hostname === 'localhost')
    ? "http://127.0.0.1:8000"
    : "/api";

export const getAuthHeaders = (token: string | null) => ({
    "Authorization": `Bearer ${token}`,
    "Content-Type": "application/json",
});

export const api = {
    async fetch(endpoint: string, options: RequestInit = {}) {
        const response = await fetch(`${API_URL}${endpoint}`, options);
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `API request failed with status ${response.status}`);
        }
        return response.json();
    }
};
