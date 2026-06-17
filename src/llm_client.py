import re
import requests
from langchain_ollama import OllamaLLM
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.app_config import OLLAMA_MODEL, OLLAMA_BASE_URL, GROQ_API_KEY, GROQ_MODEL, LLM_PROVIDER, PRIORITY_CONFIG_FILE, load_priority_config, get_priority_text
from src.prompts import QUERY_GENERATION_PROMPT, GROQ_QUERY_GENERATION_PROMPT, SUMMARIZATION_PROMPT, TREND_COMPARISON_PROMPT

class GroqLLM:
    """Simple wrapper for Groq API using requests."""
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.url = "https://api.groq.com/openai/v1/chat/completions"

    def invoke(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1
        }
        resp = requests.post(self.url, headers=headers, json=data, timeout=30)
        if resp.status_code != 200:
            raise RuntimeError(f"Groq API Error: {resp.text}")
        return resp.json()["choices"][0]["message"]["content"]

class LLMClient:
    """Wrapper for LLM operations with retry mechanism."""
    
    def __init__(self, provider: str = LLM_PROVIDER):
        self.provider = provider
        self.model = OLLAMA_MODEL if provider == "ollama" else GROQ_MODEL
        self.base_url = OLLAMA_BASE_URL
        self.llm = None
        self.priority_config = load_priority_config()
        
    def initialize(self) -> bool:
        """Initialize the selected LLM."""
        try:
            if self.provider == "groq":
                self.llm = GroqLLM(api_key=GROQ_API_KEY, model=GROQ_MODEL)
                # Test connection implicitly if needed, or assume it works
                print(f"[OK] Groq LLM hazir ({self.model})")
                return True
            else:
                self.llm = OllamaLLM(
                    model=self.model,
                    base_url=self.base_url,
                    temperature=0.1,
                    num_predict=1024
                )
                # Test connection
                self.llm.invoke("Merhaba, hazır mısın?")
                print(f"[OK] Ollama LLM hazir ({self.model})")
                return True
        except Exception as e:
            print(f"[HATA] LLM baglanti hatasi ({self.provider}): {e}")
            return False
            
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.exceptions.ConnectionError, TimeoutError))
    )
    def generate_sql_query(self, question: str, schema_context: str = "") -> str:
        """Generate SQL query from natural language question with retry."""
        if not self.llm:
            raise RuntimeError("LLM başlatılmamış")
        
        if not schema_context:
            schema_context = "Veri şeması yüklenemedi."
            
        from datetime import datetime
        today_str = datetime.now().strftime("%Y%m%d")
        schema_context += f"\n\nBUGÜNÜN TARİHİ: {today_str} (Zaman hesaplamalarını bu tarihe göre yap)"
            
        if self.provider == "groq":
            prompt = GROQ_QUERY_GENERATION_PROMPT.format(
                schema_context=schema_context,
                question=question
            )
        else:
            prompt = QUERY_GENERATION_PROMPT.format(
                schema_context=schema_context,
                question=question
            )
            
        response = self.llm.invoke(prompt)
        
        # Clean response to get only SQL
        return self._extract_sql(response)

    def _extract_sql(self, text: str) -> str:
        """Extract SQL query from LLM response text."""
        text = text.strip()
        
        # Remove markdown code blocks
        if "```" in text:
            match = re.search(r"```(?:sql)?\s*(.*?)\s*```", text, re.DOTALL)
            if match:
                return match.group(1).strip()
        
        # Find SELECT statement
        select_match = re.search(r"(SELECT\s+.*?;)", text, re.DOTALL | re.IGNORECASE)
        if select_match:
            return select_match.group(1).strip()
        
        # If text starts with SELECT
        if text.upper().startswith("SELECT"):
            # Add semicolon if missing
            if not text.rstrip().endswith(";"):
                text = text.rstrip() + ";"
            return text.strip()
        
        # Fallback: find any line starting with SELECT
        for line in text.split("\n"):
            line = line.strip()
            if line.upper().startswith("SELECT"):
                if not line.endswith(";"):
                    line += ";"
                return line
        
        return text
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.exceptions.ConnectionError, TimeoutError))
    )
    def summarize_result(self, question: str, result: str) -> str:
        """Summarize SQL result with retry."""
        if not self.llm:
            raise RuntimeError("LLM başlatılmamış")
        
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
            
            is_meta = False
            line_lower = line_strip.lower().replace("**", "").strip()
            for phrase in meta_phrases:
                if line_lower.startswith(phrase) or line_lower == phrase.rstrip(":"):
                    is_meta = True
                    break
            if is_meta:
                continue
                
            if line_strip.startswith('-') or line_strip.startswith('*') or line_strip.startswith('•'):
                content = line_strip[1:].strip()
                if content in seen:
                    continue
                seen.add(content)
            else:
                if line_strip in seen:
                    continue
                seen.add(line_strip)
                
            cleaned.append(line)
        
        while cleaned and cleaned[-1].strip() == "":
            cleaned.pop()
        
        return "\n".join(cleaned)
