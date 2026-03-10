import requests
from langchain_ollama import OllamaLLM
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.app_config import OLLAMA_MODEL, OLLAMA_BASE_URL, PRIORITY_CONFIG_FILE, load_priority_config, get_priority_text
from src.prompts import QUERY_GENERATION_PROMPT, SUMMARIZATION_PROMPT, TREND_COMPARISON_PROMPT

class LLMClient:
    """Wrapper for Ollama LLM operations with retry mechanism."""
    
    def __init__(self, model: str = OLLAMA_MODEL, base_url: str = OLLAMA_BASE_URL):
        self.model = model
        self.base_url = base_url
        self.llm = None
        self.priority_config = load_priority_config()
        
    def initialize(self) -> bool:
        """Initialize the Ollama LLM."""
        try:
            self.llm = OllamaLLM(
                model=self.model,
                base_url=self.base_url,
                temperature=0.1,
                num_predict=1024
            )
            # Test connection
            test_response = self.llm.invoke("Merhaba, hazır mısın?")
            print(f"✅ Ollama LLM hazır ({self.model})")
            return True
        except Exception as e:
            print(f"❌ Ollama bağlantı hatası: {e}")
            print(f"   Ollama'nın çalıştığından emin olun: ollama serve")
            print(f"   Model yüklü mü kontrol edin: ollama pull {self.model}")
            return False
            
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.exceptions.ConnectionError, TimeoutError))
    )
    def generate_es_query(self, question: str, schema_context: str = "") -> str:
        """Generate Elasticsearch query from natural language question with retry."""
        if not self.llm:
            raise RuntimeError("LLM başlatılmamış")
        
        # Schema context yoksa varsayılan metni kullan
        if not schema_context:
            schema_context = "Veri şeması yüklenemedi."
            
        prompt = QUERY_GENERATION_PROMPT.format(question=question, schema_context=schema_context)
        response = self.llm.invoke(prompt)
        
        # Clean response to get only JSON
        return self._extract_json(response)

    def _extract_json(self, text: str) -> str:
        """Extract the first complete JSON object from text."""
        text = text.strip()
        
        # Remove markdown code blocks
        if "```" in text:
            import re
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
            if match:
                return match.group(1)
                
        # Find the first complete JSON object by tracking brace depth
        start = text.find("{")
        if start == -1:
            return text
            
        depth = 0
        in_string = False
        escape_next = False
        
        for i in range(start, len(text)):
            char = text[i]
            
            if escape_next:
                escape_next = False
                continue
                
            if char == '\\' and in_string:
                escape_next = True
                continue
                
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
                
            if in_string:
                continue
                
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    return text[start:i+1]
            
        # Fallback: return from first { to last }
        end = text.rfind("}")
        if end != -1:
            return text[start:end+1]
            
        return text
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.exceptions.ConnectionError, TimeoutError))
    )
    def summarize_result(self, question: str, result: str) -> str:
        """Summarize Elasticsearch result in Turkish with retry."""
        if not self.llm:
            raise RuntimeError("LLM başlatılmamış")
        
        # Öncelik metnini config'den dinamik olarak oluştur
        priority_text = get_priority_text(self.priority_config)
        prompt = SUMMARIZATION_PROMPT.format(
            question=question,
            result=result,
            priority_text=priority_text
        )
        response = self.llm.invoke(prompt)
        return self._clean_output(response.strip())

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.exceptions.ConnectionError, TimeoutError))
    )
    def compare_trend_results(self, question: str, current_result: str, previous_result: str) -> str:
        """Compare two time period results for trend analysis."""
        if not self.llm:
            raise RuntimeError("LLM başlatılmamış")
        
        priority_text = get_priority_text(self.priority_config)
        prompt = TREND_COMPARISON_PROMPT.format(
            question=question,
            current_result=current_result,
            previous_result=previous_result,
            priority_text=priority_text
        )
        response = self.llm.invoke(prompt)
        return self._clean_output(response.strip())
        
    def _clean_output(self, text: str) -> str:
        """Tekrarlanan satırları ve meta-yorum satırlarını temizler."""
        lines = text.split('\n')
        cleaned = []
        seen = set()
        
        # Temizlenecek meta-yorum ifadeleri
        meta_phrases = [
            "ozet:", "özet:", "sonuç:", "sonuc:", "cevap:", 
            "işte özet:", "rapor:", "analiz:", "ancak,",
            "doğrudan cevap ver:", "sayıları ve yüzdeleri kullan:",
            "listener/action geçerse", "kritik bulgularda kısa",
            "birden fazla kategori varsa", "iç talimatlar",
            "trend varsa karşılaştır", "aksiyon önerisi:"
        ]
        
        for line in lines:
            line_strip = line.strip()
            if not line_strip:
                cleaned.append(line)
                continue
            
            # Meta yorumları atla
            is_meta = False
            line_lower = line_strip.lower().replace("**", "").strip()
            for phrase in meta_phrases:
                if line_lower.startswith(phrase) or line_lower == phrase.rstrip(":"):
                    is_meta = True
                    break
            if is_meta:
                continue
                
            # Tekrar kontrolü (sayılar hariç)
            # Eğer satır bir liste elemanıysa daha sıkı kontrol yap
            if line_strip.startswith('-') or line_strip.startswith('*') or line_strip.startswith('•'):
                # Liste elemanının içeriğini al
                content = line_strip[1:].strip()
                if content in seen:
                    continue
                seen.add(content)
            else:
                if line_strip in seen:
                    continue
                seen.add(line_strip)
                
            cleaned.append(line)
        
        # Sondaki boş satırları temizle
        while cleaned and cleaned[-1].strip() == "":
            cleaned.pop()
        
        return "\n".join(cleaned)
