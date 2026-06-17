from typing import Dict, List, Optional, Any
from thefuzz import process
from src.db_client import SAPApiClient

class SchemaRegistry:
    """
    Registry for valid SAP API field values.
    Used to map fuzzy user inputs to exact database values.
    """
    
    # Static aliases for common terms (Synonym Mapping)
    ALIASES = {
        "EVTACT": {
            "zafiyet": "SecurityBridge License Check",
            "kod hatasi": "Vulnerable program execution",
            "vulnerability": "Vulnerable program execution",
            "yetki": "Repeating authorization failures",
            "authorization failure": "Repeating authorization failures",
            "kilitli hesap": "Locked account, attempt to login",
            "locked account": "Locked account, attempt to login",
            "rfc": "RFC usage alerts",
            "self created": "Potential login with a self-created user",
            "supheli kullanici": "Potential login with a self-created user"
        }
    }

    def __init__(self, db_client: SAPApiClient):
        self.db_client = db_client
        self.field_values: Dict[str, List[Any]] = {
            "EVTACT": [],
            "EVTSYS": [],
            "EVTPRO": [],
            "EVTUSR": [],
            "EVTTER": [],
            "EVTOBJ": []
        }
        self.initialized = False

    def load_schema(self):
        """Fetches unique values from SAP API to build the registry."""
        print("[*] Sema yukleniyor (SAP API'den benzersiz degerler aliniyor)...")
        
        if not self.db_client.session:
            # Force connection if not active
            self.db_client.connect()

        # Define fields to load. Added more fields as requested.
        fields_to_load = ["EVTACT", "EVTSYS", "EVTTER", "EVTOBJ", "EVTUSR", "EVTPRO", "EVTMSG_V2", "SYSTYPT", "EVTTCODE"]
        
        for field in fields_to_load:
            values = self.db_client.get_unique_values(field, size=100)
            if values:
                self.field_values[field] = values
                print(f"    - {field}: {len(values)} deger yuklendi")
            else:
                print(f"    - {field}: Deger bulunamadi")
        
        # Fallback degerler
        if not self.field_values["EVTACT"]:
             self.field_values["EVTACT"] = [
                 "Vulnerable program execution",
                 "Repeating authorization failures",
                 "Locked account, attempt to login", 
                 "RFC usage alerts",
                 "Potential login with a self-created user"
             ]

        self.initialized = True
        print("[OK] Sema kaydi (Schema Registry) hazir.")

    def match_value(self, field: str, value: Any, threshold: int = 70) -> Optional[Any]:
        if not value:
            return None
            
        field = field.upper()
        if field == "EVTOBJ":
            try:
                val_str = str(value).strip()
                if val_str in [str(v) for v in self.field_values.get("EVTOBJ", [])]:
                    return val_str
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
        choices = self.field_values.get(field, [])
        if not choices:
            return value

        # 2. Exact Match Check (Case insensitive)
        for choice in choices:
            if str(choice).lower() == value_lower:
                return choice

        # 3. Fuzzy Matching
        best_match = process.extractOne(value_str, [str(c) for c in choices])
        
        if best_match:
            match_value, score = best_match
            if score >= threshold:
                for choice in choices:
                    if str(choice) == match_value:
                        return choice
        
        return None

    def get_schema_context(self) -> str:
        if not self.initialized:
            return "Sema henuz yuklenmedi."
            
        context_parts = []
        
        if self.field_values.get("EVTPRO"):
            programs = sorted([str(p) for p in self.field_values["EVTPRO"][:15]])
            context_parts.append(f"- EVTPRO (Program - Top 15): {', '.join(programs)}")
            
        if self.field_values.get("EVTUSR"):
            users = sorted([str(u) for u in self.field_values["EVTUSR"][:20]])
            context_parts.append(f'- EVTUSR (User - Top 20): {", ".join(users)}')
            
        if self.field_values.get("EVTSYS"):
            systems = sorted([str(s) for s in self.field_values["EVTSYS"]])
            context_parts.append(f"- EVTSYS (System): {', '.join(systems)}")

        if self.field_values.get("EVTACT"):
            actions = sorted([str(a) for a in self.field_values["EVTACT"][:20]])
            context_parts.append(f"- EVTACT (Action): {', '.join(actions)}")
            
        if self.field_values.get("EVTMSG_V2"):
            msgs = sorted([str(m) for m in self.field_values["EVTMSG_V2"][:15]])
            context_parts.append(f"- EVTMSG_V2 (Functions): {', '.join(msgs)}")
            
        if self.field_values.get("SYSTYPT"):
            types = sorted([str(t) for t in self.field_values["SYSTYPT"][:5]])
            context_parts.append(f"- SYSTYPT (Sys Types): {', '.join(types)}")
            
        return "\n".join(context_parts)
