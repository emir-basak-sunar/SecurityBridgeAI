import os as _os
import json

# Elasticsearch Configuration
ES_HOST = "http://localhost:9200"
ES_INDEX = "sap-security-logs"
ES_TIMEOUT = 30

# LLM Configuration
OLLAMA_MODEL = "llama3.1:8b"
OLLAMA_BASE_URL = "http://localhost:11434"

# Priority Configuration
try:
    PRIORITY_CONFIG_FILE = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "priority_config.json")
except Exception:
    # Fallback if path resolution fails
    PRIORITY_CONFIG_FILE = "priority_config.json"

def load_priority_config() -> dict:
    """priority_config.json dosyasından öncelik konfigürasyonunu yükler."""
    try:
        with open(PRIORITY_CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
            return config
    except FileNotFoundError:
        return {
            "action_priority": {
                "Vulnerable program execution": {"level": 1, "label": "KRİTİK", "icon": "🔴"},
                "Locked account, attempt to login": {"level": 2, "label": "ORTA", "icon": "🟡"},
                "Repeating authorization failures": {"level": 3, "label": "DÜŞÜK", "icon": "🟢"},
                "RFC usage alerts": {"level": 5, "label": "BİLGİ", "icon": "🔵"},
                "Potential login with a self-created user": {"level": 2, "label": "YÜKSEK", "icon": "🟠"},
            },
            "listener_priority": {
                1079: {"level": 1, "label": "KRİTİK - Zafiyet"},
            }
        }

def get_priority_text(config: dict) -> str:
    """Öncelik konfigürasyonundan kısa referans tablosu oluşturur."""
    lines = []
    
    # Sadece Listener → Action eşleşmesi (kısa tablo)
    if "listener_priority" in config:
        for listener, info in config["listener_priority"].items():
            action = info.get("action", "")
            label = info.get("label", "")
            lines.append(f"- {listener} = {action} ({label})")
            
    return "\n".join(lines)
