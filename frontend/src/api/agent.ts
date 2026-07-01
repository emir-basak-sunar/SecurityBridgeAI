import type { AgentResponse, StatusResponse } from "../types";
import { getApiBase } from "./config";

export async function askAgent(question: string, provider: string = "ollama"): Promise<AgentResponse> {
    const res = await fetch(`${getApiBase()}/api/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, provider }),
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
}

export async function getStatus(): Promise<StatusResponse> {
    const res = await fetch(`${getApiBase()}/api/status`);
    if (!res.ok) throw new Error(`Status check failed`);
    return res.json();
}

export async function getSchema(): Promise<Record<string, string[]>> {
    const res = await fetch(`${getApiBase()}/api/schema`);
    if (!res.ok) throw new Error(`Schema fetch failed`);
    const data = await res.json();
    return data.fields || {};
}
