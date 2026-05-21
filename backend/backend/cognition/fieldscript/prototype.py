from cognition.fieldscript.engine import FieldScript
import torch

def run_cognitive_cycle():
    print("\n" + "="*50)
    print(" FIELD AGENT COGNITIVE CYCLE — START")
    print("="*50)
    
    # Инициализация нашего DSL
    agent = FieldScript(dim=256)
    
    # 1. Наблюдаем новую концепцию
    new_concept = "NARE-Field provides intelligence-per-token maximization."
    agent.observe(new_concept)
    
    # 2. Пытаемся осмыслить (Reasoning)
    # Если энергия системы высокая, значит концепция противоречит старым знаниям
    agent.reason(depth=12)
    
    # 3. Ищем аналогии в памяти
    agent.recall("intelligence efficiency metrics")
    
    # 4. Проверяем стабильность концепции (Инвариант)
    agent.stabilize()
    
    # 5. Если всё ок — фиксируем в вечности
    agent.commit("IpT Maximization is a core Field property.")
    
    print("="*50)
    print(" CYCLE COMPLETE. FIELD IS HARMONIOUS.")
    print("="*50 + "\n")

if __name__ == "__main__":
    with torch.no_grad():
        run_cognitive_cycle()
