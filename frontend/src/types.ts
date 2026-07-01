export interface RequestTiming {
    schema_ms?: number;
    sql_generation_ms?: number;
    sap_query_ms?: number;
    summary_ms?: number;
    sap_query_current_ms?: number;
    sap_query_previous_ms?: number;
    trend_summary_ms?: number;
    total_ms?: number;
}

export interface AgentResponse {
    question: string;
    sql_query: string | null;
    sql_result: Record<string, unknown> | null;
    summary: string;
    query_type: "normal" | "trend";
    error: string | null;
    execution_time_ms: number;
    timing?: RequestTiming;
    trend_data?: {
        current_week_query?: string;
        previous_week_query?: string;
        current_rows?: number;
        previous_rows?: number;
    };
}

export interface StatusResponse {
    sap_hana: boolean;
    llm: boolean;
    llm_provider: string;
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
