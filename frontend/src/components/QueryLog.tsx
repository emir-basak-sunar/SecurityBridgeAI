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

    const syntaxHighlightSQL = (sql: string): string => {
        // Highlight SQL keywords
        const keywords = [
            "SELECT", "FROM", "WHERE", "AND", "OR", "GROUP BY", "ORDER BY",
            "LIMIT", "COUNT", "SUM", "AVG", "MAX", "MIN", "AS", "DESC", "ASC",
            "BETWEEN", "IN", "NOT", "NULL", "IS", "LIKE", "JOIN", "ON",
            "LEFT", "RIGHT", "INNER", "OUTER", "HAVING", "DISTINCT",
            "DATE_TRUNC", "NOW", "INTERVAL", "TO_CHAR", "CASE", "WHEN", "THEN", "END",
        ];

        let result = sql.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

        // Highlight string literals
        result = result.replace(/'([^']*)'/g, `<span class="sql-string">'$1'</span>`);

        // Highlight keywords (case insensitive, word boundary)
        for (const kw of keywords) {
            const regex = new RegExp(`\\b(${kw})\\b`, "gi");
            result = result.replace(regex, `<span class="sql-keyword">$1</span>`);
        }

        // Highlight numbers
        result = result.replace(/\b(\d+)\b/g, `<span class="sql-number">$1</span>`);

        return result;
    };

    const syntaxHighlightJSON = (json: string): string => {
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

    const getDisplayContent = (): { text: string; isSQL: boolean } => {
        if (!response) return { text: "", isSQL: false };
        if (activeTab === "query") {
            return { text: response.sql_query || "null", isSQL: true };
        } else {
            const obj = response.sql_result;
            if (!obj) return { text: "null", isSQL: false };
            return { text: JSON.stringify(obj, null, 2), isSQL: false };
        }
    };

    const { text: displayText, isSQL } = getDisplayContent();

    if (loading) {
        return (
            <div className="query-log-card">
                <div className="card-header">
                    <span className="card-icon">SQL</span>
                    <span className="card-title">SQL Sorgu Log</span>
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
                    <span className="card-icon">SQL</span>
                    <span className="card-title">SQL Sorgu Log</span>
                </div>
                <div className="card-body">
                    <div className="empty-state">
                        <p>Sorgu çalıştırıldığında SQL burada görünecek</p>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="query-log-card">
            <div className="card-header">
                <span className="card-icon">SQL</span>
                <span className="card-title">SQL Sorgu Log</span>
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
                    onClick={() => copyToClipboard(displayText)}
                    title="Kopyala"
                >
                    {copied ? "✓" : "⎘"}
                </button>
            </div>
            <div className="card-body">
                <pre className="json-viewer">
                    <code
                        dangerouslySetInnerHTML={{
                            __html: isSQL
                                ? syntaxHighlightSQL(displayText)
                                : syntaxHighlightJSON(displayText),
                        }}
                    />
                </pre>
            </div>
        </div>
    );
}
