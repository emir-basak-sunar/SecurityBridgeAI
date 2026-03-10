import json
import copy
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple

from src.db_client import ElasticsearchClient
from src.llm_client import LLMClient
from src.schema import SchemaRegistry
from src.app_config import PRIORITY_CONFIG_FILE, load_priority_config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Comparison keywords — ONLY explicit week-to-week references trigger dual-query
# Generic "trend" goes through normal query (LLM can generate date_histogram)
COMPARISON_KEYWORDS = [
    "geçen hafta", "gecen hafta", "önceki hafta", "onceki hafta",
    "geçen haftaya göre", "önceki haftaya göre",
    "karşılaştır", "karsilastir", "kıyasla", "kiyasla",
    "haftalık değişim", "haftalik degisim",
    "haftaya kıyasla", "hafta farkı", "hafta farki"
]


def format_es_result(result: Dict[str, Any]) -> str:
    """Format Elasticsearch result for LLM consumption with size limit."""
    result_str = json.dumps(result, ensure_ascii=False, indent=2)
    MAX_CHARS = 4000
    if len(result_str) > MAX_CHARS:
        result_str = result_str[:MAX_CHARS] + "\n... (sonuç kısaltıldı)"
    return result_str


def is_comparison_question(question: str) -> bool:
    """Detect if the question explicitly asks for week-to-week comparison."""
    q_lower = question.lower()
    return any(keyword in q_lower for keyword in COMPARISON_KEYWORDS)


def add_time_range(query: Dict[str, Any], gte: str, lt: str) -> Dict[str, Any]:
    """Add a time range filter to an ES query without mutating the original."""
    q = copy.deepcopy(query)
    
    range_filter = {"range": {"@timestamp": {"gte": gte, "lt": lt}}}
    
    if "query" not in q:
        q["query"] = range_filter
    else:
        # Wrap existing query in a bool must with the range
        existing_query = q["query"]
        q["query"] = {
            "bool": {
                "must": [existing_query, range_filter]
            }
        }
    
    return q


class SAPLogAnalysisAgent:
    
    def __init__(self):
        self.es_client = ElasticsearchClient()
        self.llm_client = LLMClient()
        self.schema_registry = SchemaRegistry(self.es_client)
        self.initialized = False
        self.priority_config = load_priority_config()

    def initialize(self) -> bool:
        """Initialize all components."""
        print("=" * 60)
        print("SAP Guvenlik Log Analiz Ajani - SecurityBridgeAI (Modular v2)")
        print("=" * 60)
        
        if not self.es_client.connect():
            return False
        if not self.llm_client.initialize():
            return False
        self.schema_registry.load_schema()
        
        self.initialized = True
        return True

    def ask(self, question: str) -> str:
        """Process natural language question using LLM-generated ElasticSearch DSL."""
        if not self.initialized:
            return "Agent başlatılmadı."
            
        print(f"\nSoru: {question}")
        print("-" * 40)
        
        # Step 1: Query Generation (LLM)
        print("[1] Elasticsearch Sorgusu Oluşturuluyor (LLM)...")
        try:
            schema_context = self.schema_registry.get_schema_context()
            es_query_str = self.llm_client.generate_es_query(question, schema_context)
            
            try:
                es_query = json.loads(es_query_str)
            except json.JSONDecodeError as e:
                print(f"    ⚠️ Geçersiz JSON: {es_query_str}")
                print(f"    Hata detayı: {e}")
                return "Sorgu oluşturulamadı (JSON hatası). LLM bozuk çıktı üretti."
            
            # Sanitize: remove placeholder values
            es_query = self._sanitize_query(es_query)
                
            print(f"    Sorgu: {json.dumps(es_query, ensure_ascii=False)[:300]}...")
            
        except Exception as e:
            return f"Sorgu oluşturma hatası: {e}"

        # Step 2: Check if this is an explicit week-comparison question
        if is_comparison_question(question):
            return self._execute_trend_analysis(es_query, question)
        else:
            return self._execute_normal_query(es_query, question)

    def _execute_normal_query(self, es_query: Dict[str, Any], question: str) -> str:
        print("[2] Sorgu Çalıştırılıyor...")
        try:
            result = self.es_client.execute_query(es_query)
        except Exception as e:
            return f"Sorgu hatası: {e}"

        if "error" in result:
            error_msg = result.get("error", "Bilinmeyen hata")
            print(f"    ⚠️ Elasticsearch hatası: {str(error_msg)[:200]}")
            return f"Elasticsearch sorgusu başarısız oldu. Hata: {str(error_msg)[:200]}"

        print("[3] Sonuç Özetleniyor...")
        try:
            formatted_result = format_es_result(result)
            summary = self.llm_client.summarize_result(question, formatted_result)
        except Exception as e:
            return f"Özetleme hatası: {e}"
            
        return summary

    def _execute_trend_analysis(self, base_query: Dict[str, Any], question: str) -> str:
        """Execute dual-query trend analysis: this week vs previous week."""
        print("[2] Trend Analizi: İki dönem karşılaştırılıyor...")
        
        # Strip any time range the LLM may have added (agent controls time)
        clean_query = self._strip_time_range(base_query)
        
        # Calculate actual dates for logging
        now = datetime.now()
        current_start = (now - timedelta(days=7)).strftime("%Y-%m-%d %H:%M")
        current_end = now.strftime("%Y-%m-%d %H:%M")
        previous_start = (now - timedelta(days=14)).strftime("%Y-%m-%d %H:%M")
        previous_end = (now - timedelta(days=7)).strftime("%Y-%m-%d %H:%M")
        
        # Create two time-ranged queries
        current_week_query = add_time_range(clean_query, "now-7d", "now")
        previous_week_query = add_time_range(clean_query, "now-14d", "now-7d")
        
        print(f"    📅 Bu hafta:     {current_start} → {current_end}")
        print(f"    📅 Önceki hafta: {previous_start} → {previous_end}")
        print(f"    Sorgu A (bu hafta):     {json.dumps(current_week_query, ensure_ascii=False)}")
        print(f"    Sorgu B (önceki hafta): {json.dumps(previous_week_query, ensure_ascii=False)}")
        
        # Execute both
        try:
            print("    [2a] Bu hafta sorgulanıyor...")
            current_result = self.es_client.execute_query(current_week_query)
            
            if "error" in current_result:
                error_msg = current_result.get("error", "")
                print(f"    ⚠️ Bu hafta sorgusu hatası: {str(error_msg)[:200]}")
                return f"Trend analizi başarısız: Bu hafta sorgusu hatası."
            
            print("    [2b] Önceki hafta sorgulanıyor...")
            previous_result = self.es_client.execute_query(previous_week_query)
            
            if "error" in previous_result:
                error_msg = previous_result.get("error", "")
                print(f"    ⚠️ Önceki hafta sorgusu hatası: {str(error_msg)[:200]}")
                return f"Trend analizi başarısız: Önceki hafta sorgusu hatası."
                
        except Exception as e:
            return f"Trend sorgusu hatası: {e}"

        # Log hit counts
        current_hits = current_result.get("hits", {}).get("total", {}).get("value", "?")
        previous_hits = previous_result.get("hits", {}).get("total", {}).get("value", "?")
        print(f"    📊 Bu hafta toplam hit: {current_hits}")
        print(f"    📊 Önceki hafta toplam hit: {previous_hits}")

        # Step 3: Compare with LLM
        print("[3] Trend Karşılaştırması Yapılıyor (LLM)...")
        try:
            current_formatted = format_es_result(current_result)
            previous_formatted = format_es_result(previous_result)
            
            summary = self.llm_client.compare_trend_results(
                question, current_formatted, previous_formatted
            )
        except Exception as e:
            return f"Trend karşılaştırma hatası: {e}"
            
        return summary

    def _strip_time_range(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Remove any @timestamp range filter from the query so agent can add its own."""
        q = copy.deepcopy(query)
        
        if "query" not in q:
            return q
        
        qpart = q["query"]
        
        # Case 1: Direct range on @timestamp
        if "range" in qpart and "@timestamp" in qpart.get("range", {}):
            del q["query"]
            return q
        
        # Case 2: Inside bool.must or bool.filter
        if "bool" in qpart:
            for clause_type in ["must", "filter"]:
                if clause_type not in qpart["bool"]:
                    continue
                clauses = qpart["bool"][clause_type]
                if isinstance(clauses, list):
                    cleaned = [c for c in clauses if not ("range" in c and "@timestamp" in c.get("range", {}))]
                    if cleaned:
                        qpart["bool"][clause_type] = cleaned
                    else:
                        del qpart["bool"][clause_type]
            
            # If bool is now empty, remove query entirely
            if not qpart.get("bool"):
                del q["query"]
        
        return q

    def _sanitize_query(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Remove placeholder values like <terminal_adı> from query."""
        import re
        q_str = json.dumps(query, ensure_ascii=False)
        
        if re.search(r'<[a-zA-ZçğıöşüÇĞİÖŞÜ_\s]+>', q_str):
            print("    ⚠️ Placeholder değer tespit edildi, temizleniyor...")
            cleaned = self._remove_placeholder_clauses(query)
            print(f"    ✅ Temizlenmiş sorgu: {json.dumps(cleaned, ensure_ascii=False)[:300]}")
            return cleaned
        
        return query

    def _contains_placeholder(self, obj) -> bool:
        """Check if a value contains a placeholder at any depth."""
        import re
        placeholder_re = re.compile(r'<[a-zA-ZçğıöşüÇĞİÖŞÜ_\s]+>')
        if isinstance(obj, str):
            return bool(placeholder_re.search(obj))
        elif isinstance(obj, list):
            return any(self._contains_placeholder(item) for item in obj)
        elif isinstance(obj, dict):
            return any(self._contains_placeholder(v) for v in obj.values())
        return False

    def _remove_placeholder_clauses(self, obj) -> Any:
        """Recursively remove dict entries whose values contain placeholders at any depth."""
        if isinstance(obj, dict):
            cleaned = {}
            for k, v in obj.items():
                if self._contains_placeholder(v):
                    continue  # Skip entire key-value pair
                cleaned_v = self._remove_placeholder_clauses(v)
                if cleaned_v is not None:
                    cleaned[k] = cleaned_v
            return cleaned
        elif isinstance(obj, list):
            cleaned_list = []
            for item in obj:
                if self._contains_placeholder(item):
                    continue  # Skip list items with placeholders
                cleaned_item = self._remove_placeholder_clauses(item)
                if isinstance(cleaned_item, dict) and not cleaned_item:
                    continue
                if cleaned_item is not None:
                    cleaned_list.append(cleaned_item)
            return cleaned_list
        return obj

    def reload_priority_config(self):
        """Reloads priority config."""
        self.priority_config = load_priority_config()
        self.llm_client.priority_config = self.priority_config
        print("Öncelik ayarları yenilendi.")
    
    def generate_executive_summary(self):
        """Generates executive summary."""
        return "Executive summary module pending refactor."
