# -*- coding: utf-8 -*-
"""
SecurityBridgeAI — Flask API Server
Exposes the SAPLogAnalysisAgent via REST endpoints for the React frontend.
"""
import sys
import os
import json

# Add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from flask import Flask, request, jsonify
from flask_cors import CORS
from src.agent import SAPLogAnalysisAgent

app = Flask(__name__)
CORS(app)  # Allow React dev server (localhost:5173)

# Global agent instance
agent = None


def get_agent():
    global agent
    if agent is None:
        agent = SAPLogAnalysisAgent()
        agent.initialize()
    return agent


@app.route("/api/ask", methods=["POST"])
def api_ask():
    """Process a natural language question and return structured response."""
    data = request.get_json()
    if not data or "question" not in data:
        return jsonify({"error": "question field is required"}), 400
    
    question = data["question"].strip()
    if not question:
        return jsonify({"error": "question cannot be empty"}), 400
    
    a = get_agent()
    result = a.ask_structured(question)
    
    # Ensure JSON serializable (remove non-serializable objects)
    return jsonify(_safe_json(result))


@app.route("/api/status", methods=["GET"])
def api_status():
    """Check Elasticsearch and Ollama connectivity."""
    a = get_agent()
    
    es_ok = False
    ollama_ok = False
    
    try:
        es_ok = a.es_client.client.ping()
    except Exception:
        pass
    
    try:
        import requests as req
        r = req.get("http://localhost:11434/api/version", timeout=3)
        ollama_ok = r.status_code == 200
    except Exception:
        pass
    
    return jsonify({
        "elasticsearch": es_ok,
        "ollama": ollama_ok,
        "agent_initialized": a.initialized,
    })


@app.route("/api/schema", methods=["GET"])
def api_schema():
    """Return loaded schema field values."""
    a = get_agent()
    try:
        ctx = a.schema_registry.get_schema_context()
        # Also return raw field values for data explorer filters
        fields = {}
        for field_name, values in a.schema_registry.field_values.items():
            fields[field_name] = list(values)[:50]
        return jsonify({"schema_context": ctx, "fields": fields})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _safe_json(obj):
    """Make object JSON-serializable by converting non-standard types."""
    if isinstance(obj, dict):
        return {k: _safe_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_safe_json(item) for item in obj]
    elif isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    else:
        return str(obj)


if __name__ == "__main__":
    print("\n🚀 SecurityBridgeAI Web Server starting...")
    print("   API: http://localhost:5000")
    print("   UI:  http://localhost:5173 (React dev server)\n")
    
    # Initialize agent on startup
    get_agent()
    
    app.run(host="0.0.0.0", port=5000, debug=False)
