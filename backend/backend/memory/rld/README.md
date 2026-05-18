# Dynamic Segmented Memory

Dynamic Segmented Memory (DSM) is a standalone memory architecture for models.
It is a library-level memory core and is not tied to any agent framework.

The goal is simple: the model should not attend over all long-term memory at once.
DSM stores knowledge as segmented, categorized, graph-linked memory and routes each
query to a small active context.

## Recursive Latent DNA (RLD)

This repository also includes **Recursive Latent DNA**: a standalone reasoning-memory
layer built on the same DSM idea. DSM routes memory segments; RLD routes reusable
reasoning genes.

RLD implements the architecture:

```text
trajectory τ=(s0,a0,s1,a1,...,sn)
        ↓ f(τ)
reasoning gene g = compact transformation delta
        ↓ DSM controller
G* = {gi : P(gi | x) > θ}
        ↓ sparse weighted activation
LLM active context = query + selected reasoning genes
        ↓ sleep
prune + merge + stabilize
```

### RLD components

- **Reasoning genes**: compact structured modules containing task context,
  transformation delta, intermediate reasoning steps, tools and solution schema.
- **DSM controller**: computes `P(g_i | x)` from dense compatibility, trigger-term
  overlap, historical success, stability and utility, then activates Top-k genes.
- **DSM-backed retrieval**: each reasoning gene is also indexed as a
  `DynamicSegmentedMemory` segment, so activation first uses DSM category routing,
  dense/sparse retrieval and graph expansion, then reranks candidates with `DSMPolicy`.
- **Dynamic weighting**: active genes receive per-query weights, similar to sparse
  MoE gating.
- **Sleep/consolidation**: low-value genes are pruned, compatible genes merge into
  higher-level chromosomes and reused genes are stabilized into cleaner forms.
- **Formal latent interfaces**: `LatentEncoder`, `GeneExtractor` and `DSMPolicy`
  make the prototype replaceable with learned encoders or neural controllers.
- **Activation traces**: every candidate gene records dense compatibility,
  trigger overlap, success/stability/utility/reuse scores, `P(g_i | x)`, weight
  and threshold decision.
- **Gene schema**: `rld schema` / `rld_schema` expose the JSON structure for
  storing and inspecting genes.

### RLD usage

```python
from rld import RecursiveLatentDNA

rld = RecursiveLatentDNA(".rld/genes.json")

rld.observe(
    "Fix a websocket timeout in an async Rust service",
    states=[
        "Connections drop after idle period.",
        "Missing heartbeat deadline causes stale sockets.",
        "Patch adds ping/pong timeout and bounded backpressure.",
    ],
    actions=[
        "Locate websocket loop",
        "Add heartbeat deadline",
        "Validate cancellation-safe cleanup",
    ],
    final_answer="Use ping deadlines, bounded channels and cleanup on cancellation.",
    tools_used=["rg", "pytest"],
    utility=0.92,
)

context = rld.active_context("How do I fix another Rust websocket timeout?", top_k=3)
model_input = context.context_text

report = rld.consolidate()
rld.save()
```

CLI:

```bash
rld --storage .rld/genes.json observe "Fix websocket timeout" \
  --action "Locate websocket loop" \
  --action "Add heartbeat deadline" \
  --answer "Use ping deadlines and bounded channels"

rld --storage .rld/genes.json activate "Another websocket timeout"
rld --storage .rld/genes.json consolidate
rld schema
```

### Research-grade extension points

The default implementation is deterministic and local, but the architecture mirrors
the theory closely:

```python
from rld import RecursiveLatentDNA, WeightedDSMPolicy, HashLatentEncoder

rld = RecursiveLatentDNA(
    ".rld/genes.json",
    latent_encoder=HashLatentEncoder(),      # replace with neural hidden-state encoder
    dsm_policy=WeightedDSMPolicy(top_k=4),   # replace with learned P(g|x) controller
)
```

Custom implementations can plug in:

- `LatentEncoder`: maps task states into explicit latent states and latent deltas.
- `GeneExtractor`: implements `g=f(τ)` from raw trajectories.
- `DSMPolicy`: implements `P(g_i | x)`, sparse thresholding and activation weights.

By default RLD now runs on top of a DSM backend:

```text
ReasoningGene -> DSM segment/category/graph index -> DSM route(q) -> DSMPolicy rerank
```

This makes DSM the candidate generator and graph-linked memory substrate, while RLD
adds reasoning-gene semantics and consolidation.

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

The included embedding model is deterministic and local. A production model can
replace it with any encoder that exposes:

```python
class Encoder:
    dim: int
    def encode(self, text: str) -> list[float]: ...
```

## Install for development

```bash
python -m pip install -e ".[dev]"
```

## Internal model usage

```python
from dsm import DynamicSegmentedMemory

memory = DynamicSegmentedMemory(".dsm/memory.json")

memory.write(
    "Rust websocket services need bounded channels, ping timeouts and cancellation-safe tasks.",
    category_path="Programming → Rust → Async",
    importance=0.9,
)

active = memory.active_context("Как исправить websocket timeout в Rust?", k=3)

# Pass only active.context_text into the model, not the whole memory store.
model_input = active.context_text

# After the model answers, write the interaction back.
memory.update_from_interaction(
    "Как исправить websocket timeout в Rust?",
    "Use bounded channels, ping/pong deadlines and cancellation-safe task cleanup.",
)
memory.save()
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
src/dsm/memory.py    # DynamicSegmentedMemory engine
```

## Checks

```bash
python -m pytest
python -m ruff check src tests
python -m compileall -q src
```
