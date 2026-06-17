import { useState, useEffect, useRef } from "react";
import "./styles/App.css";
import { Sidebar } from "./components/Sidebar";
import { QueryInput } from "./components/QueryInput";
import { AIResponse } from "./components/AIResponse";
import { QueryLog } from "./components/QueryLog";
import { DataExplorer } from "./components/DataExplorer";
import { Dashboard } from "./components/Dashboard";
import { askAgent, getStatus } from "./api/agent";
import type { AgentResponse, StatusResponse, QueryHistoryItem } from "./types";

function App() {
  const [response, setResponse] = useState<AgentResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<StatusResponse>({ postgresql: false, ollama: false, agent_initialized: false });
  const [history, setHistory] = useState<QueryHistoryItem[]>([]);
  const [activePanel, setActivePanel] = useState<"response" | "data" | "dashboard">("dashboard");
  const mainRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const s = await getStatus();
        setStatus(s);
      } catch {
        setStatus({ postgresql: false, ollama: false, agent_initialized: false });
      }
    };
    checkStatus();
    const interval = setInterval(checkStatus, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleAsk = async (question: string, provider: string = "ollama") => {
    setLoading(true);
    setResponse(null);
    try {
      const result = await askAgent(question, provider);
      setResponse(result);

      const item: QueryHistoryItem = {
        id: Date.now().toString(),
        question,
        timestamp: new Date(),
        queryType: result.query_type,
        executionTime: result.execution_time_ms,
        success: !result.error,
      };
      setHistory((prev) => [item, ...prev]);
      setActivePanel("response");
    } catch (err) {
      setResponse({
        question,
        sql_query: null,
        sql_result: null,
        summary: "",
        query_type: "normal",
        error: `Bağlantı hatası: ${err}`,
        execution_time_ms: 0,
      });
    } finally {
      setLoading(false);
    }
  };

  const handleHistoryClick = (item: QueryHistoryItem) => {
    handleAsk(item.question, "ollama"); // Default back to ollama or keep track of provider in history if needed
  };

  return (
    <div className="app">
      <Sidebar status={status} history={history} onHistoryClick={handleHistoryClick} />
      <main className="main" ref={mainRef}>
        <QueryInput onSubmit={handleAsk} loading={loading} />

        <div className="panel-tabs">
          <button
            className={`panel-tab ${activePanel === "response" ? "active" : ""}`}
            onClick={() => setActivePanel("response")}
          >
            <span className="tab-icon"></span> AI Analiz
          </button>
          <button
            className={`panel-tab ${activePanel === "data" ? "active" : ""}`}
            onClick={() => setActivePanel("data")}
          >
            <span className="tab-icon"></span> Veri Gezgini
          </button>
          <button
            className={`panel-tab ${activePanel === "dashboard" ? "active" : ""}`}
            onClick={() => setActivePanel("dashboard")}
          >
            <span className="tab-icon"></span> Dashboard
          </button>
        </div>

        <div className="panels">
          {activePanel === "response" ? (
            <div className="panels-row">
              <AIResponse response={response} loading={loading} />
              <QueryLog response={response} loading={loading} />
            </div>
          ) : activePanel === "data" ? (
            <DataExplorer response={response} />
          ) : (
            <Dashboard />
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
