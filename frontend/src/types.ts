export interface AgentResponse {
    question: string;
    es_query: Record<string, unknown> | null;
    es_result: Record<string, unknown> | null;
    summary: string;
    query_type: "normal" | "trend";
    error: string | null;
    execution_time_ms: number;
    trend_data?: {
        current_week_query?: Record<string, unknown>;
        previous_week_query?: Record<string, unknown>;
        current_hits?: number;
        previous_hits?: number;
    };
}

export interface StatusResponse {
    elasticsearch: boolean;
    ollama: boolean;
    agent_initialized: boolean;
}

export interface QueryHistoryItem {
    id: string;
    question: string;
    timestamp: Date;
    queryType: "normal" | "trend";
    executionTime: number;
    success: boolean;
}
