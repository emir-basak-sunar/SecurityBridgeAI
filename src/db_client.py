from typing import Optional, Dict, Any
from elasticsearch import Elasticsearch, ConnectionError, TransportError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.app_config import ES_HOST, ES_INDEX

class ElasticsearchClient:
    """Wrapper for Elasticsearch operations."""
    
    def __init__(self, host: str = ES_HOST, index: str = ES_INDEX):
        self.host = host
        self.index = index
        self.client: Optional[Elasticsearch] = None
    
    def connect(self) -> bool:
        """Establish connection to Elasticsearch."""
        try:
            self.client = Elasticsearch(self.host)
            info = self.client.info()
            print(f"✅ Elasticsearch bağlantısı kuruldu (v{info['version']['number']})")
            return True
        except Exception as e:
            print(f"❌ Elasticsearch bağlantı hatası: {e}")
            return False
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ConnectionError, TransportError))
    )
    def _execute_with_retry(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Execute ES query with retry logic."""
        if not self.client:
            raise RuntimeError("Elasticsearch bağlantısı yok")
        
        return self.client.search(
            index=self.index,
            **query
        )

    def execute_query(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an Elasticsearch query."""
        try:
            response = self._execute_with_retry(query)
            # Convert ObjectApiResponse to dict if necessary
            if hasattr(response, "body"):
                return response.body
            if hasattr(response, "to_dict"):
                return response.to_dict()
            return dict(response)
        except Exception as e:
            return {"error": str(e)}

    def get_index_info(self) -> Optional[Dict[str, Any]]:
        """Get index statistics."""
        if not self.client:
            return None
        
        try:
            return self.client.count(index=self.index)
        except Exception:
            return None
            
    def get_unique_values(self, field: str, size: int = 1000) -> list:
        """Fetch unique values for a specific field to build the schema registry."""
        if not self.client:
            return []
            
        query = {
            "size": 0,
            "aggs": {
                "unique_values": {
                    "terms": {"field": field, "size": size}
                }
            }
        }
        
        try:
            result = self.execute_query(query)
            buckets = result.get("aggregations", {}).get("unique_values", {}).get("buckets", [])
            return [b["key"] for b in buckets]
        except Exception as e:
            print(f"Error fetching unique values for {field}: {e}")
            return []
