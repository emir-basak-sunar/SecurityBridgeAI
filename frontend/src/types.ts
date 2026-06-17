export interface AgentResponse {
    question: string;
    sql_query: string | null;
    sql_result: Record<string, unknown> | null;
    summary: string;
    query_type: "normal" | "trend";
    error: string | null;
    execution_time_ms: number;
    trend_data?: {
        current_week_query?: string;
        previous_week_query?: string;
        current_rows?: number;
        previous_rows?: number;
    };
}

export interface StatusResponse {
    postgresql: boolean;
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
