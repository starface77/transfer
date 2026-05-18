"""
Tiido Series 1: Production Runner (Local Model)
Uses Qwen2.5-1.5B-Instruct directly via transformers.
"""
import sys
import os
import time
import torch
from pathlib import Path
from transformers import AutoModelForCausalLM, AutoTokenizer

# Ensure paths are correct
sys.path.append(str(Path(__file__).parent.parent))

from dsm.tiido import TiidoDSMRuntime, simple_model

def load_local_qwen():
    name = "Qwen/Qwen2.5-1.5B-Instruct"
    print(f"\n[System] Loading Local Brain: {name}...")
    t0 = time.time()
    
    tokenizer = AutoTokenizer.from_pretrained(name, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        name, 
        torch_dtype=torch.float32, # CPU friendly
        device_map="cpu", 
        trust_remote_code=True
    )
    print(f"[System] Brain active in {time.time()-t0:.1f}s")
    return model, tokenizer

def run_tiido():
    print("\n" + "═"*50)
    print("   TIIDO SERIES 1 - PRODUCTION RUNTIME (LOCAL)")
    print("═"*50)

    # 1. Load the Model
    model, tokenizer = load_local_qwen()

    # 2. Initialize Tiido Runtime
    storage = Path("storage/personal_ai_v1.json")
    runtime = TiidoDSMRuntime(storage_path=storage)
    
    # 3. Define the Model Interface
    @simple_model
    def chat_model(context: str, message: str) -> str:
        prompt = (
            "You are Tiido Series 1, a high-end personal AI and the intellectual accelerator for Danil. "
            "Your personality is minimalist, direct, and elite. You are a co-creator of Field and NARE Labs. "
            "Never act like a generic assistant. Be a partner. "
            f"Current DSM Context:\n{context}\n\n"
            f"User (Danil): {message}\n"
            "Tiido:"
        )
        
        messages = [{"role": "user", "content": prompt}]
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(text, return_tensors="pt")
        
        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=150, do_sample=True, temperature=0.7)
            
        response = tokenizer.decode(out[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()
        return response

    # 4. Interaction Loop
    print("\n[Tiido]: Ready. My memory is initialized.")
    
    while True:
        user_input = input("\n[Danil]: ").strip()
        if user_input.lower() in ["exit", "quit"]:
            runtime.export_snapshot()
            print("Snapshot exported. Systems offline.")
            break
        
        if not user_input:
            continue

        # Recall Context
        active = runtime.prepare(user_input, k=3)
        if active.selected:
            print(f" [DSM Recall]: {', '.join([item.segment.category_path[-1] for item in active.selected])}")

        # Generate Response
        turn = runtime.respond(user_input, model=chat_model)
        print(f"\n[Tiido]: {turn.answer}")
        
        if turn.learned_segment_ids:
            print(f" (Learned {len(turn.learned_segment_ids)} new insights)")

if __name__ == "__main__":
    run_tiido()
