import type { StatusResponse, QueryHistoryItem } from "../types";
import "./Sidebar.css";

interface Props {
    status: StatusResponse;
    history: QueryHistoryItem[];
    onHistoryClick: (item: QueryHistoryItem) => void;
}

export function Sidebar({ status, history, onHistoryClick }: Props) {
    return (
        <aside className="sidebar">
            <div className="sidebar-header">
                <div className="logo">
                    <img src="/logo.png" alt="AI SecurityBridge" className="logo-img" />
                </div>
            </div>

            <div className="sidebar-status">
                <h3 className="sidebar-section-title">Sistem Durumu</h3>
                <div className="status-items">
                    <div className="status-item">
                        <span className={`status-dot ${status.postgresql ? "online" : "offline"}`} />
                        <span className="status-label">PostgreSQL</span>
                        <span className={`status-badge ${status.postgresql ? "online" : "offline"}`}>
                            {status.postgresql ? "Online" : "Offline"}
                        </span>
                    </div>
                    <div className="status-item">
                        <span className={`status-dot ${status.ollama ? "online" : "offline"}`} />
                        <span className="status-label">Ollama LLM</span>
                        <span className={`status-badge ${status.ollama ? "online" : "offline"}`}>
                            {status.ollama ? "Online" : "Offline"}
                        </span>
                    </div>
                    <div className="status-item">
                        <span className={`status-dot ${status.agent_initialized ? "online" : "offline"}`} />
                        <span className="status-label">Agent</span>
                        <span className={`status-badge ${status.agent_initialized ? "online" : "offline"}`}>
                            {status.agent_initialized ? "Hazır" : "Bekliyor"}
                        </span>
                    </div>
                </div>
            </div>

            <div className="sidebar-history">
                <h3 className="sidebar-section-title">Sorgu Geçmişi</h3>
                {history.length === 0 ? (
                    <p className="history-empty">Henüz sorgu yapılmadı</p>
                ) : (
                    <ul className="history-list">
                        {history.map((item) => (
                            <li
                                key={item.id}
                                className={`history-item ${item.success ? "" : "failed"}`}
                                onClick={() => onHistoryClick(item)}
                                title={item.question}
                            >
                                <div className="history-question">{item.question}</div>
                                <div className="history-meta">
                                    <span className={`history-type ${item.queryType}`}>
                                        {item.queryType === "trend" ? "Trend" : "Sorgu"}
                                    </span>
                                    <span className="history-time">{item.executionTime}ms</span>
                                </div>
                            </li>
                        ))}
                    </ul>
                )}
            </div>

            <div className="sidebar-footer">
                <span className="footer-text">SecurityBridgeAI v3.0 — SQL</span>
            </div>
        </aside>
    );
}
