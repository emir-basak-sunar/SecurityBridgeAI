import os
import json

# SAP REST API Configuration (HANA üzerinden ABAP REST servisi)
SAP_API_URL = os.getenv(
    "SAP_API_URL",
    "http://solmandev.btctr.local:8000/sap/bc/rest/zbtc_json_api/driver",
)
SAP_USER = os.getenv("SAP_USER", "ARGE_USER")
SAP_PASSWORD = os.getenv("SAP_PASSWORD", "Ekonum01")

# Table name
SAP_TABLE = '"/ABEX/SEFWE"'


# LLM Configuration
# ollama = local Ollama | aicore = Ollama BYOM on SAP AI Core | groq = Groq cloud
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# SAP AI Core BYOM Ollama (Llama 3.1 8B deployment URL from AI Core)
AICORE_CLIENT_ID = os.getenv("AICORE_CLIENT_ID", "")
AICORE_CLIENT_SECRET = os.getenv("AICORE_CLIENT_SECRET", "")
AICORE_AUTH_URL = os.getenv("AICORE_AUTH_URL", "")
AICORE_OLLAMA_DEPLOYMENT_URL = os.getenv("AICORE_OLLAMA_DEPLOYMENT_URL", "")
AICORE_RESOURCE_GROUP = os.getenv("AICORE_RESOURCE_GROUP", "default")

# Groq Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3-32b")

# Priority Configuration
try:
    PRIORITY_CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "priority_config.json")
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
