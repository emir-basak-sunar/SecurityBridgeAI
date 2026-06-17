import sys
import os

# Add parent directory to path so imports work
# This allows 'import src.agent' to work from src/main.py
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from src.agent import SAPLogAnalysisAgent

def main():
    agent = SAPLogAnalysisAgent()
    if not agent.initialize():
        print("Başlatılamadı.")
        return

    print("\n[OK] Sistem Hazir. Cikmak icin 'q' veya 'exit' yazin.")
    print("   Özel komutlar: 'özet', 'reload'")
    
    while True:
        try:
            user_input = input("\nSoru > ").strip()
            
            if user_input.lower() in ['q', 'exit', 'quit']:
                print("Güle güle!")
                break
                
            if not user_input:
                continue
                
            if user_input.lower() == "reload":
                agent.reload_priority_config()
                continue
                
            if user_input.lower() == "özet":
                print(agent.generate_executive_summary())
                continue
                
            response = agent.ask(user_input)
            print(f"\n{response}\n")
            
        except KeyboardInterrupt:
            print("\nÇıkış yapılıyor...")
            break
        except Exception as e:
            print(f"\nHata: {e}")

if __name__ == "__main__":
    main()
