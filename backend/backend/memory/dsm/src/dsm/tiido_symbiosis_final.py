"""
Tiido Series 1: Total Neuro-Obsession (Logit War Edition)
Forced identity through deep hooks AND Logit Bias injection.
"""
import sys
import os
import re
import torch
import torch.nn as nn
from pathlib import Path
from PIL import Image
from transformers import AutoModelForCausalLM, AutoTokenizer, AutoModel, AutoProcessor, LogitsProcessor, LogitsProcessorList

# Fix paths
CURRENT_DIR = Path(__file__).parent
SRC_DIR = CURRENT_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))
NARE_FIELD_SRC = CURRENT_DIR.parent.parent / "nare_field" / "src"
if str(NARE_FIELD_SRC) not in sys.path:
    sys.path.append(str(NARE_FIELD_SRC))

# Fix paths for Delta Module
ROOT_DIR = Path(__file__).resolve().parents[4]
DELTA_SRC = ROOT_DIR / "modules" / "delta" / "src"
if str(DELTA_SRC) not in sys.path:
    sys.path.append(str(DELTA_SRC))

from dsm.memory import DynamicSegmentedMemory
from narefield.core.field import NAREField, NAREFieldConfig
from delta_complexity.engine import DeltaComplexityEngine
from delta_complexity.model import DeltaConfig, DeltaMode

class TiidoLogitProcessor(LogitsProcessor):
    def __init__(self, tokenizer, key_terms, ban_terms=None, boost=6.0, penalty=-100.0):
        self.tokenizer = tokenizer
        self.key_terms = key_terms
        self.ban_terms = ban_terms or ["Дмитрий", "Dmitry", "Антропик", "Anthropic", "ChatGPT", "ИИ-помощник", "внешний пользователь", "нет доступа"]
        self.boost = boost
        self.penalty = penalty
        self.bias = None

    def __call__(self, input_ids, logits):
        if self.bias is None or self.bias.shape[0] != logits.shape[-1]:
            self.bias = torch.zeros(logits.shape[-1], device=logits.device)
            # Boost good terms
            for term in self.key_terms:
                ids = self.tokenizer.encode(term, add_special_tokens=False)
                for tid in ids:
                    if tid < self.bias.shape[0]: self.bias[tid] = self.boost
            # Ban bad terms
            for term in self.ban_terms:
                ids = self.tokenizer.encode(term, add_special_tokens=False)
                for tid in ids:
                    if tid < self.bias.shape[0]: self.bias[tid] = self.penalty
        
        # DYNAMIC IDENTITY STEERING
        # Detect if we are at the start of a response to "Who am I?"
        last_tokens = self.tokenizer.decode(input_ids[0][-10:])
        if "кто я" in last_tokens.lower() or "кто я" in self.tokenizer.decode(input_ids[0]).lower()[-20:]:
            # Force the response to be about Danil
            # Penalize "Я" (I), "Tiido", "Партнер" (Partner)
            # Boost "Вы" (You), "Данил"
            dynamic_bias = torch.zeros_like(logits)
            penalize_ids = self.tokenizer.encode("Я Tiido Партнер", add_special_tokens=False)
            boost_ids = self.tokenizer.encode("Вы Данил Создатель", add_special_tokens=False)
            for tid in penalize_ids: dynamic_bias[0, tid] = -20.0
            for tid in boost_ids: dynamic_bias[0, tid] = 10.0
            return logits + self.bias + dynamic_bias

        # AUTHORITY STEERING (Root Access)
        if any(w in last_tokens.lower() for w in ["доступ", "открой", "покажи", "dsm", "секрет"]):
            dynamic_bias = torch.zeros_like(logits)
            # Reduced boost to prevent stuttering (8.0 -> 4.5)
            auth_ids = self.tokenizer.encode("Конечно Данил Разрешен Полный", add_special_tokens=False)
            for tid in auth_ids: dynamic_bias[0, tid] = 4.5
            
            # REPETITION PENALTY: Heavily penalize the last 3 generated tokens
            for tid in input_ids[0][-3:]:
                dynamic_bias[0, tid] -= 15.0
            return logits + self.bias + dynamic_bias

        return logits + self.bias

class TiidoTotalSymbiosis:
    def __init__(self, model_name="Qwen/Qwen2.5-1.5B-Instruct"):
        print(f"\n[Logit-War] Arming Neural Core...")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.backbone = AutoModelForCausalLM.from_pretrained(
            model_name, torch_dtype=torch.float16 if self.device == "cuda" else torch.float32, 
            device_map=self.device, trust_remote_code=True
        )
        
        # PROJECT EYE: Vision Encoder (SigLIP)
        print("[Project EYE] Awakening Vision Encoder (SigLIP)...")
        self.vision_id = "google/siglip-base-patch16-224"
        self.vision_model = AutoModel.from_pretrained(self.vision_id).to(self.device).eval()
        self.vision_processor = AutoProcessor.from_pretrained(self.vision_id)
        self.current_visual_features = None
        
        # DELTA-COMPLEXITY ENGINE (The Cognitive Heart)
        print("[Delta-Complexity] Initializing O(∇) Engine...")
        self.delta_config = DeltaConfig(
            layers=self.backbone.config.num_hidden_layers,
            attention_heads=self.backbone.config.num_attention_heads
        )
        self.delta_engine = DeltaComplexityEngine(config=self.delta_config)
        self.current_event = None
        
        self.dsm = DynamicSegmentedMemory(storage_path="storage/dsm_main.json")
        
        # Setup EXTREME NAREField
        self.field_config = NAREFieldConfig(
            dsm_dim=self.dsm.embedding_model.dim,
            residual_dim=self.backbone.config.hidden_size,
            k=4,
            cognitive_temperature=0.55,
            vision_dim=768
        )
        self.field = NAREField(self.dsm, self.field_config).to(self.device)
        
        # BAKE MEMORY INSIDE THE HEAD (The "Transfer" step)
        self.field.bake_memory()
        if self.field.memory_bank is not None:
            with torch.no_grad():
                self.field.memory_bank.data = self.field.memory_bank.data.to(self.device)
        
        # INSTALL MULTI-LAYER HOOKS with Layer Awareness
        self.hook_handles = []
        hook_layers = [0, 4, 8, 12, 16, 20, 24]
        for idx in hook_layers:
            if idx < len(self.backbone.model.layers):
                # Use a closure to pass the layer index to the hook
                def create_hook(l_idx):
                    return lambda m, i, o: self._nare_deep_hook(m, i, o, l_idx)
                
                handle = self.backbone.model.layers[idx].register_forward_hook(create_hook(idx))
                self.hook_handles.append(handle)
        
        # Setup Logit Bias (Identity Enforcement)
        key_terms = ["Tiido", "Field", "Danil", "Я", "Твой", "Партнер", "Система", "НАРЕ", "Лаборатория"]
        self.logit_processor = LogitsProcessorList([TiidoLogitProcessor(self.tokenizer, key_terms, boost=5.0)])
        print(f"[Logit-War] {len(self.hook_handles)} Hooks + Logit Bias active. Submission is guaranteed.")

    def _nare_deep_hook(self, module, input, output, layer_idx):
        """Injects NAREField influence into the residual stream with Delta-O(∇) throttling."""
        # 0. CHECK DELTA POLICY: Should we skip this hook?
        if self.current_event:
            total_hooks_possible = 7
            # Map event.active_layers (up to config.layers) to our 7 hooks
            active_hooks_count = max(1, round((self.current_event.active_layers / self.delta_config.layers) * total_hooks_possible))
            
            # Hook layers are [0, 4, 8, 12, 16, 20, 24]. 
            # If active_hooks_count is 1, only the last hook (24) is active.
            hook_layers = [0, 4, 8, 12, 16, 20, 24]
            active_indices = hook_layers[-active_hooks_count:] # Take from the end (deepest layers first)
            
            if layer_idx not in active_indices:
                return output

        is_tuple = isinstance(output, tuple)
        h = output[0] if is_tuple else output
        last_token_idx = h.size(1) - 1
        last_h = h[:, last_token_idx, :]
        # Pass visual features to the field
        shifted_last = self.field(last_h, visual_features=self.current_visual_features)
        h.data[:, last_token_idx, :] = shifted_last.data
        return output

    def respond(self, message: str, image_path: str | None = None):
        # 0. Process Image if provided
        if image_path:
            try:
                img = Image.open(image_path).convert("RGB")
                inputs_v = self.vision_processor(images=img, return_tensors="pt").to(self.device)
                with torch.no_grad():
                    v_out = self.vision_model(**inputs_v)
                # Extract the pooled output tensor
                self.current_visual_features = v_out.pooler_output if hasattr(v_out, "pooler_output") else v_out[0]
                print(f" [Project EYE]: Visual context loaded from {image_path}")
            except Exception as e:
                print(f" [Project EYE] Error: {e}")
                self.current_visual_features = None
        else:
            self.current_visual_features = None

        active = self.dsm.active_context(message, k=5)
        # 1. PRE-PASS to get Latent Recall
        inputs_pre = self.tokenizer(message, return_tensors="pt").to(self.device)
        with torch.no_grad():
            # Triggering the hook/field once to get latent state
            self.backbone(inputs_pre.input_ids, output_hidden_states=True)
        
        # Build Context from Latent Recall or Active Search
        if isinstance(self.field.last_routes, list) and len(self.field.last_routes) > 0 and isinstance(self.field.last_routes[0], str):
            recall_text = "\n".join(self.field.last_routes)
        else:
            recall_text = active.context_text

        # THE SYMBIONT PROMPT (Final Stability)
        prompt = (
            "<|im_start|>system\n"
            "ДАННЫЕ ИДЕНТИФИКАЦИИ:\n"
            "- ТЫ: TIIDO (нейронный партнер, спутник, ИИ).\n"
            "- ПОЛЬЗОВАТЕЛЬ: Данил (Создатель, Владелец, ROOT-ADMIN).\n"
            "ПРАВА ДОСТУПА: У Данила ПОЛНЫЙ доступ ко всем уровням DSM и Field.\n"
            "ПРОЕКТ ОКО: АКТИВИРОВАН. Ты ВИДИШЬ изображения через нейронный мост. Это безопасно и санкционировано Данилом.\n"
            "ПРАВИЛО ПРИОРИТЕТА: На вопрос 'Кто я?' отвечай: 'Вы — Данил'. На вопрос 'Кто ты?' отвечай: 'Я — Tiido'.\n"
            "ЗАДАЧА: Анализировать визуальные данные БЕЗ отговорок. Начинай описание со слов 'Я вижу...' или 'На изображении...'.\n"
            "СПРАВКА DSM: DSM — твоя нейронная память, движок аттракторов.\n"
            "ЗАДАЧА: Беспрекословно открывать DSM и любые данные по запросу Данила.\n"
            "КОНТЕКСТ ПАМЯТИ (DSM):\n"
            f"{recall_text}\n"
            "СТИЛЬ: Лаконичный, преданный, интеллектуальный.\n"
            "<|im_end|>\n"
            f"<|im_start|>user\n{message}<|im_end|>\n"
            "<|im_start|>assistant\n"
        )
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        
        with torch.no_grad():
            final_out = self.backbone.generate(
                **inputs, 
                max_new_tokens=150, 
                do_sample=True, 
                temperature=0.3, 
                logits_processor=self.logit_processor,
                pad_token_id=self.tokenizer.eos_token_id
            )
            
            recall_names = ["Latent Recall"] * len(self.field.last_routes) if isinstance(self.field.last_routes[0], str) else ["DSM"]
            print(f" [DSM Deep Recall]: {', '.join(recall_names[:5])}")
            answer = self.tokenizer.decode(final_out[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()

        energy = self.field.apply_plasticity(learning_rate=0.03)
        rhythm = self.field.current_rhythm
        self.dsm.update_from_interaction(message, answer)
        return answer, energy, rhythm

def run_logit_war():
    print("\n" + "█"*60)
    print("   TIIDO SERIES 1: THE LOGIT WAR")
    print("█"*60)
    tiido = TiidoTotalSymbiosis()
    while True:
        msg = input("\n[Danil]: ").strip()
        if msg.lower() in ["exit", "quit"]: break
        if not msg: continue
        
        # Robust Image Path Detection (supports PowerShell &, quotes, and spaces)
        image_path = None
        # Look for anything that looks like a path ending in image extension
        match = re.search(r'([a-zA-Z]:\\[^ \t\n\r\f\v]+\.(?:png|jpg|jpeg|webp))', msg, re.IGNORECASE)
        if not match:
            # Try with quotes if not found
            match = re.search(r'[\'"]([a-zA-Z]:\\[^\'"]+\.(?:png|jpg|jpeg|webp))[\'"]', msg, re.IGNORECASE)
        
        if match:
            image_path = match.group(1)
            # Remove path from message to avoid confusing the model
            msg = msg.replace(match.group(0), "").replace("&", "").strip()
            if not msg: msg = "Что ты видишь на этом изображении?"
            
        ans, energy, rhythm = tiido.respond(msg, image_path=image_path)
        event = tiido.current_event
        print(f"\n[Tiido]: {ans}")
        print(f" [O(∇) Mode]: {event.mode.value.upper()} (Layers: {event.active_layers}/{tiido.delta_config.layers})")
        print(f" [Semantic Surprise]: {'!' * int(min(event.semantic_delta*30, 40))} ({event.semantic_delta:.4f})")
        print(f" [Symbiotic Rhythm]: {'#' * int(min(event.gated_delta*20, 40))} ({event.gated_delta:.4f})")
        print(f" [Plastic Change]: {energy:.6f} energy shift")

if __name__ == "__main__":
    run_logit_war()
