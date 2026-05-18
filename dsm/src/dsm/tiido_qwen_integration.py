import torch
import torch.nn as nn
from narefield.core.model import NAREFieldModel, NAREConfig

class TiidoQwenInModel(nn.Module):
    """
    Tiido Series 1: Qwen Backbone + NARE Memory Field Integration.
    Injects DSM attractors directly into the transformer layers.
    """
    def __init__(self, qwen_model, dsm_storage):
        super().__init__()
        self.backbone = qwen_model
        
        # Configure NARE Layer to match Qwen hidden dim (e.g., 1536)
        self.config = NAREConfig(dim=qwen_model.config.hidden_size)
        self.nare = NAREFieldModel(self.config)
        
        # Load DSM segments into the MemoryField weights
        self.initialize_memory(dsm_storage)

    def initialize_memory(self, dsm_storage):
        """Pre-loads DSM embeddings into the internal MemoryField."""
        print("[Tiido] Internalizing DSM into Neural Weights...")
        for segment in dsm_storage.segments.values():
            # Inject embedding as a stable attractor
            embedding = torch.tensor(segment.embedding).unsqueeze(0)
            self.nare.memory.learn(embedding, learn=True)
        print(f"[Tiido] {len(dsm_storage.segments)} segments internalized.")

    def forward(self, input_ids, **kwargs):
        # 1. Backbone computation (partial or full)
        outputs = self.backbone(input_ids, output_hidden_states=True, **kwargs)
        hidden_states = outputs.hidden_states[-1] # Last layer
        
        # 2. NARE Field Interaction (In-Model DSM)
        # This shifts the hidden states based on memory attractors
        nare_result = self.nare(hidden_states)
        
        # 3. Trajectory Correction
        # Inject the nare prediction back into the transformer output
        corrected_states = hidden_states + 0.2 * nare_result.prediction
        
        # 4. Final logit generation
        logits = self.backbone.lm_head(corrected_states)
        return logits

# Technical Blueprint for Devin:
# 1. Use 'register_forward_hook' on the middle layer of Qwen.
# 2. In the hook, call 'self.nare(hidden_state)'.
# 3. Add the resulting delta to the residual stream.
