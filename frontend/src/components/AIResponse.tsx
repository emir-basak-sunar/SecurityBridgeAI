import type { AgentResponse } from "../types";
import "./AIResponse.css";

interface Props {
    response: AgentResponse | null;
    loading: boolean;
}

export function AIResponse({ response, loading }: Props) {
    if (loading) {
        return (
            <div className="ai-response-card">
                <div className="card-header">
                    <span className="card-icon"></span>
                    <span className="card-title">AI Analiz</span>
                </div>
                <div className="card-body">
                    <div className="skeleton-loader">
                        <div className="skeleton-line w-90" />
                        <div className="skeleton-line w-70" />
                        <div className="skeleton-line w-80" />
                        <div className="skeleton-line w-60" />
                        <div className="skeleton-line w-75" />
                    </div>
                </div>
            </div>
        );
    }

    if (!response) {
        return (
            <div className="ai-response-card empty">
                <div className="card-header">
                    <span className="card-icon"></span>
                    <span className="card-title">AI Analiz</span>
                </div>
                <div className="card-body">
                    <div className="empty-state">
                        <div className="empty-icon">
                            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" opacity="0.3">
                                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                            </svg>
                        </div>
                        <p>SAP güvenlik sorunuzu sorarak analiz başlatın</p>
                    </div>
                </div>
            </div>
        );
    }

    const formatSummary = (text: string) => {
        // Convert markdown-like formatting to HTML
        let html = text
            .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
            .replace(/\*(.+?)\*/g, "<em>$1</em>")
            .replace(/^- (.+)$/gm, "<li>$1</li>")
            .replace(/^• (.+)$/gm, "<li>$1</li>")
            .replace(/\n\n/g, "</p><p>")
            .replace(/\n/g, "<br/>");

        // Wrap list items
        html = html.replace(/(<li>.*?<\/li>)+/gs, "<ul>$&</ul>");

        // Wrap tables if present
        if (html.includes("|")) {
            const lines = text.split("\n");
            let tableHtml = "<table><thead><tr>";
            let inTable = false;
            let headerDone = false;
            const nonTableParts: string[] = [];

            for (const line of lines) {
                if (line.includes("|") && line.trim().startsWith("|")) {
                    if (!inTable) {
                        inTable = true;
                        const cells = line.split("|").filter(c => c.trim());
                        tableHtml += cells.map(c => `<th>${c.trim()}</th>`).join("");
                        tableHtml += "</tr></thead><tbody>";
                        continue;
                    }
                    if (!headerDone && line.includes("---")) {
                        headerDone = true;
                        continue;
                    }
                    const cells = line.split("|").filter(c => c.trim());
                    tableHtml += "<tr>" + cells.map(c => `<td>${c.trim()}</td>`).join("") + "</tr>";
                } else {
                    if (inTable) {
                        tableHtml += "</tbody></table>";
                        inTable = false;
                    }
                    nonTableParts.push(line);
                }
            }
            if (inTable) tableHtml += "</tbody></table>";
            if (tableHtml.includes("<td>")) {
                html = nonTableParts.join("<br/>") + tableHtml;
            }
        }

        return `<p>${html}</p>`;
    };

    return (
        <div className="ai-response-card">
            <div className="card-header">
                <span className="card-icon"></span>
                <span className="card-title">AI Analiz</span>
                <div className="card-badges">
                    <span className={`badge ${response.query_type}`}>
                        {response.query_type === "trend" ? "Trend" : "Normal"}
                    </span>
                    <span className="badge time">{response.execution_time_ms}ms</span>
                </div>
            </div>
            <div className="card-body">
                {response.error ? (
                    <div className="error-message">
                        <span className="error-icon">!</span>
                        <span>{response.error}</span>
                    </div>
                ) : (
                    <div
                        className="response-content"
                        dangerouslySetInnerHTML={{ __html: formatSummary(response.summary) }}
                    />
                )}
            </div>
        </div>
    );
}
