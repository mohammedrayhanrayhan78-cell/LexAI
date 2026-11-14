import { API_BASE } from './config.js';

// Session handling uses HttpOnly cookies set by the backend. The browser
// attaches them automatically to same-origin requests, so this file never
// reads or stores a token.

export function redirectToLogin() {
    window.location.href = 'login.html';
}

// Ask the backend to rotate the session cookies. Resolves true on success.
export async function refreshSession() {
    try {
        const res = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
            method: 'POST',
            credentials: 'same-origin',
        });
        return res.ok;
    } catch {
        return false;
    }
}

// fetch() wrapper for authenticated API calls. On 401 it refreshes the
// session once and retries. If the session still cannot be restored, the
// user is sent to the login page.
export async function apiFetch(path, options = {}) {
    const init = { credentials: 'same-origin', ...options };
    let res = await fetch(`${API_BASE}${path}`, init);
    if (res.status === 401) {
        if (await refreshSession()) {
            res = await fetch(`${API_BASE}${path}`, init);
        }
        if (res.status === 401) {
            redirectToLogin();
        }
    }
    return res;
}

export async function checkBackendHealth() {
    const statusIndicator = document.getElementById('status-indicator');
    if (!statusIndicator) return;
    try {
        const response = await fetch(`${API_BASE}/api/v1/health`);
        if (response.ok) {
            const data = await response.json();
            statusIndicator.textContent = `Backend status: Connected (${data.status})`;
            statusIndicator.style.color = '#10a37f';
        } else {
            statusIndicator.textContent = 'Backend status: Error connecting';
            statusIndicator.style.color = '#ef4444';
        }
    } catch (error) {
        statusIndicator.textContent = 'Backend status: Offline';
        statusIndicator.style.color = '#ef4444';
    }
}
