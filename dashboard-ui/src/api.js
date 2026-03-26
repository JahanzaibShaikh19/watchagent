const API_BASE = "http://127.0.0.1:8000";

export async function getRuns(page = 1, pageSize = 25) {
    const res = await fetch(`${API_BASE}/api/runs?page=${page}&page_size=${pageSize}`);
    if (!res.ok) throw new Error("Failed to load runs");
    return res.json();
}

export async function getRun(id) {
    const res = await fetch(`${API_BASE}/api/runs/${id}`);
    if (!res.ok) throw new Error("Failed to load run detail");
    return res.json();
}

export async function getRunSteps(id) {
    const res = await fetch(`${API_BASE}/api/runs/${id}/steps`);
    if (!res.ok) throw new Error("Failed to load run steps");
    return res.json();
}

export async function getStats() {
    const res = await fetch(`${API_BASE}/api/stats`);
    if (!res.ok) throw new Error("Failed to load stats");
    return res.json();
}

export async function deleteRun(id) {
    const res = await fetch(`${API_BASE}/api/runs/${id}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Failed to delete run");
    return res.json();
}

export function openLiveStream(onMessage, onError) {
    const source = new EventSource(`${API_BASE}/api/runs/live`);
    source.onmessage = (event) => {
        try {
            const payload = JSON.parse(event.data);
            onMessage(payload);
        } catch (_err) {
            // Ignore malformed payloads.
        }
    };
    source.onerror = (err) => {
        if (onError) onError(err);
    };
    return source;
}

export async function getRunReplay(id) {
    const res = await fetch(`${API_BASE}/api/runs/${id}/replay`);
    if (!res.ok) throw new Error("Failed to load run replay");
    return res.json();
}

export async function getLicenseStatus() {
    const res = await fetch(`${API_BASE}/api/license/status`);
    if (!res.ok) throw new Error("Failed to load license status");
    return res.json();
}