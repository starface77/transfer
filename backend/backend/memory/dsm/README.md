# DSM × NARE-Field

Dynamic Segmented Memory (DSM) is a standalone memory architecture for models.
It is a library-level memory core and is not tied to any agent framework.

NARE-Field is the latent-state layer that makes DSM part of model inference:
DSM stores attractors/reasoning genes, NARE-Field observes the model residual
stream, retrieves the nearest DSM attractors and injects a gated trajectory delta
back into the hidden state.

The goal is simple: the model should not attend over all long-term memory at once.
DSM stores knowledge as segmented, categorized, graph-linked memory and routes each
query to a small active context.

## Core idea

Classic self-attention over a context of `N` tokens costs roughly `O(N²)`. Increasing
the context window alone makes the model scan more data, adds noise and still leaves
long-term memory weak.

DSM replaces one giant context with:

```text
({S_i}, T, G)
```

- `{S_i}` — independent memory segments.
- `T` — dynamic category hierarchy.
- `G` — semantic graph between segments.

For a query `q`, DSM computes:

```text
R(q) -> {S_i1, ..., S_ik}, where k << M
```

Only those selected segments form working memory:

```text
C = q + global_summary + selected_segments
```

The model can then run its normal attention over `C`, while persistent memory can
grow to millions of tokens.

## Implemented components

- **Segmented memory**: fixed-size blocks with text, description, category, embedding,
  links, priorities and timestamps.
- **Hierarchy**: a category tree such as `Programming → Rust → Async`.
- **Dynamic categorization**: new content is assigned into the hierarchy and can be
  reclustered later.
- **Semantic routing**: category beam search + segment k-NN + weighted graph expansion.
- **Hybrid search**: dense embeddings are blended with BM25-like sparse keyword
  scoring, so exact technical queries such as `строка 16` or `parser.py` win when
  they should.
- **Sparse working memory**: active context contains only routed segments.
- **Associative graph links**: related segments are connected bidirectionally with
  relation type, edge weight and reason.
- **Priorities**: relevance, importance, recency and frequency control scoring,
  decay and pruning.
- **Compression**: redundant or old groups can be collapsed into one summary segment
  with `compressed_from` provenance.
- **Consistency checks**: related segments are scanned for numeric contradictions
  such as the same subject having two different prices.
- **Fast cold start path**: the segment index uses FAISS/HNSW when `faiss-cpu` is
  installed and automatically falls back to exact cosine search.
- **Delta indexing**: `upsert_document()` rewrites only changed chunks for large
  files or repositories.
- **Cognitive loops**: `reason()` can run multiple internal memory queries before
  assembling final active context.
- **MCP server**: `dsm.mcp_server` exposes DSM as an external memory service over
  Model Context Protocol stdio tools.
- **Graph visualization**: `graph_data()` and `graph_html()` export the memory
  constellation for demos and inspection.
- **Persistence**: atomic JSON storage, no server required.
- **NARE-Field symbiosis**: PyTorch hooks observe latent state `h`, retrieve DSM
  attractors, bridge DSM vectors into the residual stream and apply gated
  injection `h = h + λΔh`.

The included embedding model is deterministic and local. A production model can
replace it with any encoder that exposes:

```python
class Encoder:
    dim: int
    def encode(self, text: str) -> list[float]: ...
```

## Install for development

```bash
python -m pip install -e ".[dev,field]"
```

## DSM × NARE-Field latent injection

```python
import torch
from torch import nn
from dsm import DynamicSegmentedMemory
from narefield import NAREField, NAREFieldAdapter, NAREFieldConfig

memory = DynamicSegmentedMemory()  # in-head DSM field
field = NAREField(
    memory,
    NAREFieldConfig(dsm_dim=memory.embedding_model.dim, residual_dim=768, k=4),
)

# Logic genes are DSM attractors, not prompts.
gene = [0.0] * memory.embedding_model.dim
gene[0] = 1.0
field.add_logic_gene("Reasoning Gene: preserve reconstruction loss logic.", gene)

transformer = nn.Sequential(...)
adapter = NAREFieldAdapter(transformer, field, "0")
output = transformer(torch.randn(1, 768))
adapter.close()
```

MVP equations implemented:

```text
m = Σ softmax(sim(h, a_i)) * a_i
Δh = bridge(m)
h' = h + λΔh
PEL = mse(predicted_latent, target_logic)
```

## Internal model usage

```python
from dsm import TiidoDSMRuntime

runtime = TiidoDSMRuntime(storage_path="storage/personal_ai_v1.json")

# Before generation, Tiido must always build DSM active context.
active = runtime.prepare("Как исправить websocket timeout в Rust?")

# Pass only active.context_text into the model.
model_input = active.context_text
```

## Tiido DSM core loop

Tiido uses DSM as the internal memory system, not as a prompt wrapper. The loop is:

```text
user_message -> dsm.active_context() -> model generation -> dsm.update_from_interaction()
```

Live Tiido memory is head-state inside the model runtime. JSON is not the source of
truth; it is only an optional snapshot/export. The default snapshot path is:

```text
storage/personal_ai_v1.json
```

Personal DNA is boosted during routing:

- `("User", "Danil", "Profile")`
- `("Identity", "Core")`

```python
from dsm import TiidoDSMRuntime

def model(context: str, message: str) -> str:
    # Your model receives Dynamic Context Injection here.
    return llm.generate(context=context, message=message)

tiido = TiidoDSMRuntime(model=model)
turn = tiido.respond("запомни: я строю Tiido на DSM")

# turn.active_context was built before generation.
# turn.learned_segment_ids were written back into DSM after generation.
tiido.export_snapshot("storage/personal_ai_v1.json")  # optional export only
```

## Maintenance loop

```python
report = memory.maintain(
    max_segments=100_000,
    min_priority=0.08,
    compress_similarity=0.78,
)

# report = {"compressed": ..., "pruned": ..., "conflicts": ...}
```

This applies priority decay, compression, pruning and consistency checks. For tighter
control, call the phases separately:

```python
memory.decay_priorities(amount=0.02)
memory.compress(similarity_threshold=0.78)
memory.prune(max_segments=100_000, min_priority=0.08)
conflicts = memory.check_consistency()
```

Each conflict records the two segment ids, the conflicting field/value pair, severity
and reason. Conflict edges are also added to the graph so retrieval can surface the
inconsistency.

## Hybrid search, delta indexing and reasoning loops

```python
memory.upsert_document(
    "src/brain.py",
    source_text,
    category_path="Code → Python",
)

results = memory.route("строка 16 brain.py", k=3)
trace = memory.reason("How does brain.py call search_memory?", loops=3, k=2)

model_input = trace.context.context_text
```

`upsert_document()` assigns stable ids per chunk (`document_id:chunk_index`) and uses
content hashes to skip unchanged chunks. `route()` combines dense similarity,
BM25-like sparse scores, exact term matches, category scores, graph expansion and
priority scores.

## MCP server

DSM is still a library, but it can be served to external models through MCP:

```bash
python -m dsm.mcp_server --storage .dsm/memory.json
```

Exposed tools:

- `dsm_write`
- `dsm_search`
- `dsm_reason`
- `dsm_upsert_document`
- `dsm_graph`

## Graph visualization

```python
from pathlib import Path
from dsm.visualize import graph_html

Path("memory.html").write_text(graph_html(memory), encoding="utf-8")
```

## Main API

```python
memory.write(text, category_path=..., importance=...)
memory.route(query, k=5)
memory.reason(query, loops=3, k=5)
memory.active_context(query, k=5, token_budget=100_000)
memory.update_from_interaction(query, answer)
memory.write_attractor(text, vector)
memory.route_by_vector(query_embedding, k=5)
memory.extract_personal_dna(user_message)
memory.learn_tiido_turn(query, answer, active_context)
memory.upsert_document(document_id, text, category_path=...)
memory.compress(similarity_threshold=...)
memory.check_consistency()
memory.rebuild_structure()
memory.prune(max_segments=..., min_priority=...)
memory.save()
```

## Structure

```text
src/dsm/models.py    # Segment, priority, category and active-context models
src/dsm/embedding.py # Local embedding protocol and default hash encoder
src/dsm/category.py  # Hierarchical category tree and dynamic clustering
src/dsm/graph.py     # Weighted associative graph memory
src/dsm/index.py     # FAISS/HNSW segment index with exact fallback
src/dsm/sparse.py    # BM25-like sparse keyword index
src/dsm/document.py  # Stable document chunking for delta indexing
src/dsm/mcp_server.py # MCP stdio server tools
src/dsm/visualize.py # Graph JSON/HTML visualization
src/dsm/tiido.py     # DSM-first Tiido personal interaction runtime
src/dsm/memory.py    # DynamicSegmentedMemory engine
src/narefield/core/field.py  # DSM attractor retrieval + residual bridge
src/narefield/core/model.py  # LatentObserver hook + forward injection adapter
src/narefield/core/losses.py # PredictionEnergyLoss + CognitiveInvariant
```

## Checks

```bash
python -m pytest
python -m ruff check src tests dsm narefield
python -m compileall -q src dsm narefield
```
