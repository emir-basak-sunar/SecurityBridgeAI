import { useState } from "react";
import type { AgentResponse } from "../types";
import "./QueryLog.css";

interface Props {
    response: AgentResponse | null;
    loading: boolean;
}

export function QueryLog({ response, loading }: Props) {
    const [copied, setCopied] = useState(false);
    const [activeTab, setActiveTab] = useState<"query" | "result">("query");

    const copyToClipboard = (text: string) => {
        navigator.clipboard.writeText(text).then(() => {
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        });
    };

    const syntaxHighlight = (json: string): string => {
        return json.replace(
            /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)/g,
            (match) => {
                let cls = "json-number";
                if (/^"/.test(match)) {
                    cls = /:$/.test(match) ? "json-key" : "json-string";
                } else if (/true|false/.test(match)) {
                    cls = "json-boolean";
                } else if (/null/.test(match)) {
                    cls = "json-null";
                }
                return `<span class="${cls}">${match}</span>`;
            }
        );
    };

    const getDisplayJson = (): string => {
        if (!response) return "";
        const obj = activeTab === "query" ? response.es_query : response.es_result;
        if (!obj) return "null";
        return JSON.stringify(obj, null, 2);
    };

    const jsonStr = getDisplayJson();

    if (loading) {
        return (
            <div className="query-log-card">
                <div className="card-header">
                    <span className="card-icon">📋</span>
                    <span className="card-title">ES Sorgu Log</span>
                </div>
                <div className="card-body">
                    <div className="skeleton-loader code">
                        <div className="skeleton-line w-60" />
                        <div className="skeleton-line w-80" />
                        <div className="skeleton-line w-40" />
                        <div className="skeleton-line w-70" />
                        <div className="skeleton-line w-50" />
                    </div>
                </div>
            </div>
        );
    }

    if (!response) {
        return (
            <div className="query-log-card empty">
                <div className="card-header">
                    <span className="card-icon">📋</span>
                    <span className="card-title">ES Sorgu Log</span>
                </div>
                <div className="card-body">
                    <div className="empty-state">
                        <p>Sorgu çalıştırıldığında ES DSL burada görünecek</p>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="query-log-card">
            <div className="card-header">
                <span className="card-icon">📋</span>
                <span className="card-title">ES Sorgu Log</span>
                <div className="log-tabs">
                    <button
                        className={`log-tab ${activeTab === "query" ? "active" : ""}`}
                        onClick={() => setActiveTab("query")}
                    >
                        Sorgu
                    </button>
                    <button
                        className={`log-tab ${activeTab === "result" ? "active" : ""}`}
                        onClick={() => setActiveTab("result")}
                    >
                        Ham Sonuç
                    </button>
                </div>
                <button
                    className={`copy-btn ${copied ? "copied" : ""}`}
                    onClick={() => copyToClipboard(jsonStr)}
                    title="Kopyala"
                >
                    {copied ? "✓" : "📋"}
                </button>
            </div>
            <div className="card-body">
                <pre className="json-viewer">
                    <code dangerouslySetInnerHTML={{ __html: syntaxHighlight(jsonStr) }} />
                </pre>
            </div>
        </div>
    );
}
