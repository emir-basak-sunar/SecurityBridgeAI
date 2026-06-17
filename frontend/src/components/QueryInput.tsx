import { useState, useRef, useEffect } from "react";
import "./QueryInput.css";

interface Props {
    onSubmit: (question: string, provider: string) => void;
    loading: boolean;
}

const EXAMPLE_QUERIES = [
    "List users with the most RFC usage alerts between 01.02.2026 and 04.02.2026 grouped by count",
    "Which terminals have the most RFC usage alerts?",
    "List all locked account login attempts in the last 7 days",
];

export function QueryInput({ onSubmit, loading }: Props) {
    const [value, setValue] = useState("");
    const [provider, setProvider] = useState("ollama");
    const inputRef = useRef<HTMLTextAreaElement>(null);

    useEffect(() => {
        inputRef.current?.focus();
    }, []);

    const handleSubmit = () => {
        const q = value.trim();
        if (q && !loading) {
            onSubmit(q, provider);
            setValue("");
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
        }
    };

    const handleExample = (q: string) => {
        if (!loading) {
            onSubmit(q, provider);
        }
    };

    return (
        <div className="query-input-wrapper">
            <div className={`query-input-container ${loading ? "loading" : ""}`}>
                <div className="query-input-icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <circle cx="11" cy="11" r="8" />
                        <path d="m21 21-4.3-4.3" />
                    </svg>
                </div>
                <select 
                    className="provider-select" 
                    value={provider} 
                    onChange={(e) => setProvider(e.target.value)}
                    disabled={loading}
                >
                    <option value="ollama">Ollama (Llama 3.1 8B)</option>
                    <option value="groq">Groq (Qwen 32B)</option>
                </select>
                <textarea
                    ref={inputRef}
                    className="query-input"
                    placeholder="SAP güvenlik sorunuzu yazın..."
                    value={value}
                    onChange={(e) => setValue(e.target.value)}
                    onKeyDown={handleKeyDown}
                    disabled={loading}
                    rows={1}
                />
                <button
                    className={`query-submit ${loading ? "loading" : ""}`}
                    onClick={handleSubmit}
                    disabled={loading || !value.trim()}
                >
                    {loading ? (
                        <div className="spinner" />
                    ) : (
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M22 2 11 13" />
                            <path d="M22 2 15 22 11 13 2 9z" />
                        </svg>
                    )}
                </button>
            </div>
            {loading && (
                <div className="loading-bar">
                    <div className="loading-bar-progress" />
                </div>
            )}
            {!loading && !value.trim() && (
                <div className="example-queries">
                    <span className="example-label">Try:</span>
                    {EXAMPLE_QUERIES.map((q, i) => (
                        <button key={i} className="example-btn" onClick={() => handleExample(q)}>
                            {q}
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
}

