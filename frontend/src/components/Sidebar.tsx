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
                    <div className="logo-icon">
                        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="url(#grad)" strokeWidth="2">
                            <defs>
                                <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
                                    <stop offset="0%" stopColor="#3b82f6" />
                                    <stop offset="100%" stopColor="#8b5cf6" />
                                </linearGradient>
                            </defs>
                            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                        </svg>
                    </div>
                    <div className="logo-text">
                        <span className="logo-title">SecurityBridge</span>
                        <span className="logo-subtitle">AI Agent</span>
                    </div>
                </div>
            </div>

            <div className="sidebar-status">
                <h3 className="sidebar-section-title">Sistem Durumu</h3>
                <div className="status-items">
                    <div className="status-item">
                        <span className={`status-dot ${status.elasticsearch ? "online" : "offline"}`} />
                        <span className="status-label">Elasticsearch</span>
                        <span className={`status-badge ${status.elasticsearch ? "online" : "offline"}`}>
                            {status.elasticsearch ? "Online" : "Offline"}
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
                                        {item.queryType === "trend" ? "📈 Trend" : "🔍 Sorgu"}
                                    </span>
                                    <span className="history-time">{item.executionTime}ms</span>
                                </div>
                            </li>
                        ))}
                    </ul>
                )}
            </div>

            <div className="sidebar-footer">
                <span className="footer-text">SecurityBridgeAI v2.0</span>
            </div>
        </aside>
    );
}
