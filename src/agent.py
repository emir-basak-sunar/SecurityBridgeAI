import json
import re
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from src.db_client import SAPApiClient
from src.llm_client import LLMClient
from src.schema import SchemaRegistry
from src.app_config import PRIORITY_CONFIG_FILE, load_priority_config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Comparison keywords — ONLY explicit week-to-week references trigger dual-query
COMPARISON_KEYWORDS = [
    "geçen hafta", "gecen hafta", "önceki hafta", "onceki hafta",
    "geçen haftaya göre", "önceki haftaya göre",
    "karşılaştır", "karsilastir", "kıyasla", "kiyasla",
    "haftalık değişim", "haftalik degisim",
    "haftaya kıyasla", "hafta farkı", "hafta farki"
]


def format_sql_result(result: Dict[str, Any]) -> str:
    """Format SQL result for LLM consumption with size limit."""
    rows = result.get("rows", [])
    row_count = result.get("row_count", len(rows))
    
    header = f"[DATA SUMMARY: {row_count} rows returned]\n"
    
    if not rows:
        return header + "No data found."
    
    # Format as a readable table string
    result_str = json.dumps(rows, ensure_ascii=False, indent=2, default=str)
    MAX_CHARS = 4000
    if len(result_str) > MAX_CHARS:
        result_str = result_str[:MAX_CHARS] + "\n... (truncated)"
    return header + result_str


def is_comparison_question(question: str) -> bool:
    """Detect if the question explicitly asks for week-to-week comparison."""
    q_lower = question.lower()
    return any(keyword in q_lower for keyword in COMPARISON_KEYWORDS)


def add_time_range_to_sql(sql: str, gte: str, lt: str) -> str:
    """Add a timestamp range filter to a SQL query."""
    time_condition = f"EVTDAT >= '{gte}' AND EVTDAT <= '{lt}'"
    
    sql_stripped = sql.rstrip(";").strip()
    
    # Check if WHERE already exists
    where_match = re.search(r'\bWHERE\b', sql_stripped, re.IGNORECASE)
    group_match = re.search(r'\bGROUP\s+BY\b', sql_stripped, re.IGNORECASE)
    order_match = re.search(r'\bORDER\s+BY\b', sql_stripped, re.IGNORECASE)
    limit_match = re.search(r'\bLIMIT\b', sql_stripped, re.IGNORECASE)
    
    if where_match:
        # Insert AND after WHERE clause, before GROUP BY/ORDER BY
        insert_pos = None
        if group_match:
            insert_pos = group_match.start()
        elif order_match:
            insert_pos = order_match.start()
        elif limit_match:
            insert_pos = limit_match.start()
        
        if insert_pos:
            sql_stripped = sql_stripped[:insert_pos] + f"AND {time_condition} " + sql_stripped[insert_pos:]
        else:
            sql_stripped += f" AND {time_condition}"
    else:
        # No WHERE, insert before GROUP BY/ORDER BY/LIMIT
        insert_pos = None
        if group_match:
            insert_pos = group_match.start()
        elif order_match:
            insert_pos = order_match.start()
        elif limit_match:
            insert_pos = limit_match.start()
        
        if insert_pos:
            sql_stripped = sql_stripped[:insert_pos] + f"WHERE {time_condition} " + sql_stripped[insert_pos:]
        else:
            sql_stripped += f" WHERE {time_condition}"
    
    return sql_stripped + ";"


def strip_time_range_from_sql(sql: str) -> str:
    """Remove any timestamp conditions from a SQL query, including complex subqueries."""
    sql = re.sub(r'--[^\n]*', '', sql)

    # Aggressively remove EVTDAT conditions
    # Matches EVTDAT op (SELECT ...) or EVTDAT op 'val'
    cleaned = re.sub(r"\bEVTDAT\s*(?:>=|<=|>|<|=)\s*(?:\([^)]+\)|'[^']*'|[\w()]+(?:\s*[-+]\s*\d+)?)", "", sql, flags=re.IGNORECASE)
    
    # Matches EVTDAT BETWEEN ... AND ...
    cleaned = re.sub(r"\bEVTDAT\s+BETWEEN\s+(?:\([^)]+\)|'[^']*'|[\w()]+)\s+AND\s+(?:\([^)]+\)|'[^']*'|[\w()]+)", "", cleaned, flags=re.IGNORECASE)
    
    # Clean up dangling ANDs/WHEREs
    cleaned = re.sub(r"\bWHERE\s+AND\b", "WHERE", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bAND\s+AND\b", "AND", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bWHERE\s+(GROUP|ORDER|LIMIT)\b", r"\1", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bAND\s+(GROUP|ORDER|LIMIT)\b", r"\1", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bWHERE\s*$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bAND\s*$", "", cleaned, flags=re.IGNORECASE)
    
    # Clean empty WHERE 
    cleaned = re.sub(r"\bWHERE\s*;\s*$", ";", cleaned, flags=re.IGNORECASE)
    
    # Remove any extra spaces
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    return cleaned.strip()


class SAPLogAnalysisAgent:
    
    def __init__(self):
        self.db_client = SAPApiClient()
        self.llm_clients = {
            "ollama": LLMClient(provider="ollama"),
            "aicore": LLMClient(provider="aicore"),
            "groq": LLMClient(provider="groq"),
        }
        self.schema_registry = SchemaRegistry(self.db_client)
        self.initialized = False
        self.priority_config = load_priority_config()

    def initialize(self) -> bool:
        """Initialize all components."""
        from src.app_config import LLM_PROVIDER

        print("=" * 60)
        print("SAP Guvenlik Log Analiz Ajani - SecurityBridgeAI (SQL v3)")
        print("=" * 60)

        sap_ok = self.db_client.connect()
        if not sap_ok:
            print("[UYARI] SAP REST API erisilemiyor (Cloud Connector / VPN gerekebilir)")

        for key in ("ollama", "aicore", "groq"):
            try:
                self.llm_clients[key].initialize()
            except Exception as e:
                print(f"[UYARI] {key} LLM baslatilamadi: {e}")

        if sap_ok:
            try:
                self.schema_registry.load_schema()
            except Exception as e:
                print(f"[UYARI] Sema yuklenemedi: {e}")

        active_llm = self.llm_clients.get(LLM_PROVIDER)
        llm_ok = bool(active_llm and active_llm.llm)
        self.initialized = sap_ok or llm_ok
        if self.initialized:
            print(f"[OK] Agent hazir (SAP: {'evet' if sap_ok else 'hayir'}, LLM: {LLM_PROVIDER})")
        return self.initialized

    def ask(self, question: str) -> str:
        """Process natural language question using LLM-generated SQL."""
        if not self.initialized:
            return "Agent başlatılmadı."
            
        print(f"\nSoru: {question}")
        print("-" * 40)
        
        # Step 1: Query Generation (LLM)
        print("[1] SQL Sorgusu Oluşturuluyor (LLM)...")
        try:
            schema_context = self.schema_registry.get_schema_context()
            sql_query = self.llm_client.generate_sql_query(question, schema_context)
            sql_query = self._sanitize_query(sql_query)
            print(f"    SQL: {sql_query[:300]}...")
        except Exception as e:
            return f"Sorgu oluşturma hatası: {e}"

        # Step 2: Check if this is an explicit week-comparison question
        if is_comparison_question(question):
            return self._execute_trend_analysis(sql_query, question)
        else:
            return self._execute_normal_query(sql_query, question)

    def ask_structured(self, question: str, provider: str = "ollama") -> Dict[str, Any]:
        """Process question and return structured result with all intermediate data."""
        import time as _time
        start = _time.time()
        
        result = {
            "question": question,
            "sql_query": None,
            "sql_result": None,
            "summary": "",
            "query_type": "normal",
            "error": None,
            "execution_time_ms": 0,
        }

        if not self.initialized:
            result["error"] = "Agent başlatılmadı."
            return result

        # Step 1: Generate SQL
        llm = self.llm_clients.get(provider, self.llm_clients["ollama"])
        try:
            schema_context = self.schema_registry.get_schema_context()
            sql_query = llm.generate_sql_query(question, schema_context)
            sql_query = self._sanitize_query(sql_query)
            result["sql_query"] = sql_query
        except Exception as e:
            result["error"] = f"Sorgu oluşturma hatası: {e}"
            result["execution_time_ms"] = int((_time.time() - start) * 1000)
            return result

        # Step 2: Execute
        if is_comparison_question(question):
            result["query_type"] = "trend"
            trend_result = self._execute_trend_structured(sql_query, question, llm)
            result.update(trend_result)
        else:
            try:
                sql_result = self.db_client.execute_query(sql_query)
                result["sql_result"] = sql_result
                if "error" in sql_result and sql_result["error"]:
                    result["error"] = f"SQL hatası: {str(sql_result['error'])[:200]}"
                else:
                    formatted = format_sql_result(sql_result)
                    result["summary"] = llm.summarize_result(question, formatted)
            except Exception as e:
                result["error"] = str(e)

        result["execution_time_ms"] = int((_time.time() - start) * 1000)
        return result

    def _execute_trend_structured(self, base_sql: str, question: str, llm: LLMClient) -> Dict[str, Any]:
        """Trend analysis returning structured data instead of string."""
        now = datetime.now()
        current_start = (now - timedelta(days=7)).strftime("%Y%m%d")
        current_end = now.strftime("%Y%m%d")
        previous_start = (now - timedelta(days=14)).strftime("%Y%m%d")
        previous_end = (now - timedelta(days=7)).strftime("%Y%m%d")
        
        clean_sql = strip_time_range_from_sql(base_sql)
        current_sql = add_time_range_to_sql(clean_sql, current_start, current_end)
        previous_sql = add_time_range_to_sql(clean_sql, previous_start, previous_end)
        
        data = {"trend_data": {}}
        try:
            current_result = self.db_client.execute_query(current_sql)
            previous_result = self.db_client.execute_query(previous_sql)
            
            if ("error" in current_result and current_result["error"]) or \
               ("error" in previous_result and previous_result["error"]):
                err_detail = current_result.get("error", "") or previous_result.get("error", "")
                data["error"] = f"Trend sorgusu hatasi: {str(err_detail)[:300]}"
                return data

            data["sql_result"] = {
                "current_week": current_result,
                "previous_week": previous_result
            }
            data["trend_data"] = {
                "current_week_query": current_sql,
                "previous_week_query": previous_sql,
                "current_rows": current_result.get("row_count", 0),
                "previous_rows": previous_result.get("row_count", 0),
            }
            
            current_fmt = format_sql_result(current_result)
            previous_fmt = format_sql_result(previous_result)
            data["summary"] = llm.compare_trend_results(question, current_fmt, previous_fmt)
        except Exception as e:
            data["error"] = str(e)
        
        return data

    def _execute_normal_query(self, sql_query: str, question: str) -> str:
        print("[2] SQL Sorgusu Çalıştırılıyor...")
        try:
            result = self.db_client.execute_query(sql_query)
        except Exception as e:
            return f"Sorgu hatası: {e}"

        if "error" in result and result["error"]:
            error_msg = result.get("error", "Bilinmeyen hata")
            print(f"    [UYARI] SQL hatasi: {str(error_msg)[:200]}")
            return f"SQL sorgusu başarısız oldu. Hata: {str(error_msg)[:200]}"

        print("[3] Sonuç Özetleniyor...")
        try:
            formatted_result = format_sql_result(result)
            summary = self.llm_client.summarize_result(question, formatted_result)
        except Exception as e:
            return f"Özetleme hatası: {e}"
            
        return summary

    def _execute_trend_analysis(self, base_sql: str, question: str) -> str:
        """Execute dual-query trend analysis: this week vs previous week."""
        print("[2] Trend Analizi: İki dönem karşılaştırılıyor...")
        
        now = datetime.now()
        current_start = (now - timedelta(days=7)).strftime("%Y%m%d")
        current_end = now.strftime("%Y%m%d")
        previous_start = (now - timedelta(days=14)).strftime("%Y%m%d")
        previous_end = (now - timedelta(days=7)).strftime("%Y%m%d")
        
        clean_sql = strip_time_range_from_sql(base_sql)
        current_sql = add_time_range_to_sql(clean_sql, current_start, current_end)
        previous_sql = add_time_range_to_sql(clean_sql, previous_start, previous_end)
        
        print(f"    Bu hafta:     {current_start} -> {current_end}")
        print(f"    Onceki hafta: {previous_start} -> {previous_end}")
        print(f"    SQL A: {current_sql}")
        print(f"    SQL B: {previous_sql}")
        
        try:
            print("    [2a] Bu hafta sorgulanıyor...")
            current_result = self.db_client.execute_query(current_sql)
            
            if "error" in current_result and current_result["error"]:
                return f"Trend analizi başarısız: {str(current_result['error'])[:200]}"
            
            print("    [2b] Önceki hafta sorgulanıyor...")
            previous_result = self.db_client.execute_query(previous_sql)
            
            if "error" in previous_result and previous_result["error"]:
                return f"Trend analizi başarısız: {str(previous_result['error'])[:200]}"
                
        except Exception as e:
            return f"Trend sorgusu hatası: {e}"

        print(f"    Bu hafta satir: {current_result.get('row_count', '?')}")
        print(f"    Onceki hafta satir: {previous_result.get('row_count', '?')}")

        print("[3] Trend Karşılaştırması Yapılıyor (LLM)...")
        try:
            current_formatted = format_sql_result(current_result)
            previous_formatted = format_sql_result(previous_result)
            
            summary = self.llm_client.compare_trend_results(
                question, current_formatted, previous_formatted
            )
        except Exception as e:
            return f"Trend karşılaştırma hatası: {e}"
            
        return summary

    def _sanitize_query(self, sql: str) -> str:
        """Remove placeholder values, comments, markdown and clean up SQL."""
        # Try to extract SQL from markdown code blocks first
        match = re.search(r'```(?:sql)?\s*(.*?)\s*```', sql, flags=re.IGNORECASE | re.DOTALL)
        if match:
            sql = match.group(1)
        else:
            # Try to find the SELECT statement directly to ignore chatty text
            match = re.search(r'(SELECT\s+.*)', sql, flags=re.IGNORECASE | re.DOTALL)
            if match:
                sql = match.group(1)
        
        # Strip SQL single-line comments (-- ...)
        sql = re.sub(r'--[^\n]*', '', sql)

        # Remove placeholder patterns like <terminal_adı>, <kullanıcı>
        if re.search(r'<[a-zA-ZçğıöşüÇĞİÖŞÜ_\s]+>', sql):
            print("    [UYARI] Placeholder deger tespit edildi, temizleniyor...")
            # Remove WHERE clauses containing placeholders
            sql = re.sub(
                r"AND\s+\w+\s*=\s*'?<[^>]+>'?\s*", "", sql, flags=re.IGNORECASE
            )
            sql = re.sub(
                r"WHERE\s+\w+\s*=\s*'?<[^>]+>'?\s*AND\s*", "WHERE ", sql, flags=re.IGNORECASE
            )
            sql = re.sub(
                r"WHERE\s+\w+\s*=\s*'?<[^>]+>'?\s*", "", sql, flags=re.IGNORECASE
            )
            print(f"    [OK] Temizlenmis SQL: {sql[:300]}")
        
        # Remove ALL semicolons (causes '%3B' URL encode errors in SAP)
        sql = sql.replace(";", "")
        
        # Remove newlines (causes '%0A' URL encode errors in SAP)
        sql = sql.replace("\n", " ").replace("\r", " ")
        
        # Remove extra spaces created by newlines
        sql = re.sub(r'\s+', ' ', sql)
        
        return sql.strip()

    def reload_priority_config(self):
        """Reloads priority config."""
        self.priority_config = load_priority_config()
        self.llm_client.priority_config = self.priority_config
        print("Öncelik ayarları yenilendi.")
    
    def generate_executive_summary(self):
        """Generates executive summary."""
        return "Executive summary module pending refactor."
