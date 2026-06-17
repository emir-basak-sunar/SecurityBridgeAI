from typing import Optional, Dict, Any, List
import requests
from requests.auth import HTTPBasicAuth
from urllib.parse import quote
import json
import urllib3
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.app_config import SAP_API_URL, SAP_USER, SAP_PASSWORD, SAP_TABLE

# Suppress SSL warnings for internal server
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class SAPApiClient:
    """Wrapper for SAP REST API operations."""
    
    def __init__(self):
        self.api_url = SAP_API_URL
        self.user = SAP_USER
        self.password = SAP_PASSWORD
        self.table = SAP_TABLE
        self.session = None
    
    def connect(self) -> bool:
        """Establish session with SAP API."""
        try:
            self.session = requests.Session()
            self.session.auth = HTTPBasicAuth(self.user, self.password)
            self.session.headers.update({
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            self.session.verify = False
            
            # Test connection
            if self.ping():
                print(f"[OK] SAP REST API baglantisi kuruldu")
                return True
            else:
                print(f"[HATA] SAP REST API baglanti testi basarisiz oldu")
                return False
        except Exception as e:
            print(f"[HATA] SAP REST API baglanti hatasi: {e}")
            return False

    def _get_session(self):
        """Get session, reconnecting if needed."""
        if self.session is None:
            self.connect()
        return self.session

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.exceptions.ConnectionError, requests.exceptions.Timeout))
    )
    def execute_query(self, sql: str, params: tuple = None) -> Dict[str, Any]:
        """Execute a SQL query via SAP REST API and return results."""
        try:
            session = self._get_session()
            
            # Format SQL with params if provided
            if params:
                # Basic string replacement for %s format
                # Note: This is rudimentary, SAP SQL syntax might require specific formatting
                for p in params:
                    if isinstance(p, str):
                        sql = sql.replace('%s', f"'{p}'", 1)
                    else:
                        sql = sql.replace('%s', str(p), 1)

            # Tarayici gibi encode et: space=%20, ama (),*,/ gibi karakterleri koru
            encoded_sql = quote(sql, safe='()*,/\'=<>!. ')
            # Sonra space'leri %20 yap
            encoded_sql = encoded_sql.replace(' ', '%20')
            full_url = f"{self.api_url}?sql_query={encoded_sql}"
            
            r = session.get(full_url, timeout=60)
            
            if r.status_code == 200:
                text = r.text.strip()
                if text.startswith('[') or text.startswith('{'):
                    try:
                        data = json.loads(text)
                        if isinstance(data, list):
                            columns = list(data[0].keys()) if data else []
                            return {
                                "columns": columns,
                                "rows": data,
                                "row_count": len(data)
                            }
                        elif isinstance(data, dict):
                            # Sometime single objects might be returned depending on API structure
                             return {
                                "columns": list(data.keys()),
                                "rows": [data],
                                "row_count": 1
                            }
                        else:
                             return {"error": f"Unexpected JSON format: {type(data)}", "rows": [], "columns": [], "row_count": 0}
                    except json.JSONDecodeError:
                        return {"error": f"Invalid JSON response: {text[:200]}", "rows": [], "columns": [], "row_count": 0}
                else:
                    return {"error": f"Non-JSON response: {text[:200]}", "rows": [], "columns": [], "row_count": 0}
            else:
                 return {"error": f"HTTP {r.status_code}: {r.text[:200]}", "rows": [], "columns": [], "row_count": 0}

        except Exception as e:
            return {"error": str(e), "rows": [], "columns": [], "row_count": 0}

    def get_table_count(self) -> int:
        """Get total row count in the table."""
        try:
            result = self.execute_query(f'SELECT COUNT(*) as CNT FROM {self.table}')
            if result and result.get("rows"):
                # SAP API lowercases column names usually, check 'cnt' or 'CNT'
                row = result["rows"][0]
                cnt = row.get("cnt", row.get("CNT", 0))
                return int(cnt)
            return 0
        except Exception:
            return 0

    def get_unique_values(self, field: str, size: int = 1000) -> list:
        """Fetch unique values for a specific field from the table."""
        if not self.session:
            return []
        
        try:
            # SAP API SQL dialect. Using DISTINCT and UP TO N ROWS / LIMIT
            sql = f'SELECT DISTINCT {field} FROM {self.table} WHERE {field} IS NOT NULL ORDER BY {field} ASC'
            result = self.execute_query(sql)
            
            if result and result.get("rows"):
                field_lower = field.lower()
                # Use lowercased field name as that's what json.loads often returns for this API
                res_list = [row.get(field_lower, row.get(field)) for row in result["rows"] if field_lower in row or field in row]
                return res_list[:size]
            return []
        except Exception as e:
            print(f"Error fetching unique values for {field}: {e}")
            return []
    
    def ping(self) -> bool:
        """Check if the API is reachable."""
        try:
            session = self._get_session()
            # Simple query to check connectivity
            encoded_sql = quote("SELECT 1 AS TEST FROM DUMMY", safe='()*,/\'=<>!. ').replace(' ', '%20')
            full_url = f"{self.api_url}?sql_query={encoded_sql}"
            r = session.get(full_url, timeout=10)
            return r.status_code == 200
        except Exception:
            return False
