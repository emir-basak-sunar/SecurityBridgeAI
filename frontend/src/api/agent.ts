import type { AgentResponse, StatusResponse } from "../types";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function askAgent(question: string, provider: string = "ollama"): Promise<AgentResponse> {
    const res = await fetch(`${API_BASE}/api/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, provider }),
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
}

export async function getStatus(): Promise<StatusResponse> {
    const res = await fetch(`${API_BASE}/api/status`);
    if (!res.ok) throw new Error(`Status check failed`);
    return res.json();
}

export async function getSchema(): Promise<Record<string, string[]>> {
    const res = await fetch(`${API_BASE}/api/schema`);
    if (!res.ok) throw new Error(`Schema fetch failed`);
    const data = await res.json();
    return data.fields || {};
}
