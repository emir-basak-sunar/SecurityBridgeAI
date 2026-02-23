from typing import Dict, List, Optional, Any
from thefuzz import process
from src.db_client import ElasticsearchClient

class SchemaRegistry:
    """
    Registry for valid Elasticsearch field values.
    Used to map fuzzy user inputs to exact database values.
    """
    
    # Static aliases for common terms (Synonym Mapping)
    ALIASES = {
        "Action": {
            "zafiyet": "Vulnerable program execution",
            "kod hatası": "Vulnerable program execution",
            "kod hatasi": "Vulnerable program execution",
            "vulnerability": "Vulnerable program execution",
            "yetki hatası": "Repeating authorization failures",
            "yetkilendirme hatası": "Repeating authorization failures",
            "authorization failure": "Repeating authorization failures",
            "yetki": "Repeating authorization failures",
            "kilitli hesap": "Locked account, attempt to login",
            "locked account": "Locked account, attempt to login",
            "rfc uyarısı": "RFC usage alerts",
            "rfc": "RFC usage alerts",
            "self created": "Potential login with a self-created user",
            "kendi oluşturduğu kullanıcı": "Potential login with a self-created user",
            "supheli kullanici": "Potential login with a self-created user"
        }
    }

    def __init__(self, es_client: ElasticsearchClient):
        self.es_client = es_client
        self.schema: Dict[str, List[Any]] = {
            "Action": [],
            "System": [],
            "Program": [],
            "User": [],
            "Terminal": [],
            "Listener": [],
            "CompanyCode": []
        }
        self.initialized = False

    def load_schema(self):
        """Fetches unique values from Elasticsearch to build the registry."""
        print("[*] Şema yükleniyor (ES'den benzersiz değerler alınıyor)...")
        
        if not self.es_client.client and not self.es_client.connect():
             print("[!] Şema yüklenemedi: ES bağlantısı yok.")
             return

        # Define fields to load
        fields_to_load = ["Action", "System", "Program", "User", "Terminal", "Listener", "CompanyCode"]
        
        for field in fields_to_load:
            # Keyword alanı ise .keyword eklemeye gerek yok çünkü ES mapping'de keyword olarak defined
            # Ancak kodda alan adları olduğu gibi kullanılıyor.
            values = self.es_client.get_unique_values(field, size=1000)
            if values:
                self.schema[field] = values
                print(f"    - {field}: {len(values)} değer yüklendi")
            else:
                print(f"    - {field}: Değer bulunamadı")
        
        # Fallback değerler (Veritabanı boşsa veya erişilemezse kodun çalışmaya devam etmesi için)
        if not self.schema["Action"]:
             self.schema["Action"] = [
                 "Vulnerable program execution",
                 "Repeating authorization failures",
                 "Locked account, attempt to login", 
                 "RFC usage alerts",
                 "Potential login with a self-created user"
             ]

        self.initialized = True
        print("✅ Şema kaydı (Schema Registry) hazır.")

    def match_value(self, field: str, value: Any, threshold: int = 70) -> Optional[Any]:
        """
        Finds the best matching value in the registry for a given field.
        
        1. Checks static aliases (if string).
        2. Checks exact match.
        3. Uses fuzzy matching (if string).
        """
        if not value:
            return None
            
        # Listener gibi sayısal alanlar için özel işlem
        if field == "Listener":
            # Gelen değer sayı ise veya sayıya çevrilebiliyorsa direkt kontrol et
            try:
                val_int = int(str(value))
                if val_int in self.schema["Listener"]:
                    return val_int
            except ValueError:
                pass
        
        value_str = str(value).strip()
        value_lower = value_str.lower()
        
        # 1. Check Aliases (Fast path)
        if field in self.ALIASES:
            for alias, target in self.ALIASES[field].items():
                if alias in value_lower:
                    return target
        
        # Get candidate list
        choices = self.schema.get(field, [])
        if not choices:
            return value # Schema boşsa, LLM'in verdiği değeri olduğu gibi döndür (Fallback)

        # 2. Exact Match Check (Case insensitive)
        for choice in choices:
            if str(choice).lower() == value_lower:
                return choice

        # 3. Fuzzy Matching
        # process.extractOne returns (match, score)
        best_match = process.extractOne(value_str, [str(c) for c in choices])
        
        if best_match:
            match_value, score = best_match
            if score >= threshold:
                # Orijinal tipi/değeri bulup döndür
                for choice in choices:
                    if str(choice) == match_value:
                        return choice
        
        # Eşleşme yoksa None dönüyor, bu durumda çağırıcı LLM'in değerini veya hata mesajı kullanabilir
        # Biz burada None dönelim, QueryBuilder karar versin
        return None

    def get_schema_context(self) -> str:
        """Returns a formatted string of the current schema for LLM context."""
        if not self.initialized:
            return "Şema henüz yüklenmedi."
            
        context_parts = []
        
        # Program listesi (popüler olanlar)
        if self.schema.get("Program"):
            programs = sorted([str(p) for p in self.schema["Program"][:15]])
            context_parts.append(f"- Program (Top 15): {', '.join(programs)}")
            
        # User listesi
        if self.schema.get("User"):
            users = sorted([str(u) for u in self.schema["User"][:20]])
            context_parts.append(f"- User (Top 20): {', '.join(users)}")
            
        # System listesi
        if self.schema.get("System"):
            systems = sorted([str(s) for s in self.schema["System"]])
            context_parts.append(f"- System: {', '.join(systems)}")
            
        # Action listesi - Listener ile ilişkilendirilmiş hali prompts.py'da var ama 
        # burada veritabanından gelen güncel listeyi de ekleyebiliriz.
        # Ancak prompts.py zaten statik tanımları içeriyor, buraya sadece dinamik olanları ekleyelim.
        
        return "\n".join(context_parts)
