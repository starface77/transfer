from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from dsm.memory import DynamicSegmentedMemory
from dsm.visualize import graph_data

JSONRPC_VERSION = "2.0"


class DsmMcpServer:
    """Minimal stdio MCP server exposing DSM as external model memory."""

    def __init__(self, memory: DynamicSegmentedMemory, rld: Any | None = None):
        self.memory = memory
        if rld is not None:
            self.rld = rld
        else:
            try:
                from rld import RecursiveLatentDNA
                self.rld = RecursiveLatentDNA(memory.storage.path.with_name("rld_genes.json"))
            except ImportError:
                self.rld = None

    def serve(self) -> None:
        for line in sys.stdin:
            if not line.strip():
                continue
            request = json.loads(line)
            response = self.handle(request)
            if response is not None:
                sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
                sys.stdout.flush()

    def handle(self, request: dict[str, Any]) -> dict[str, Any] | None:
        method = request.get("method")
        request_id = request.get("id")
        try:
            if method == "initialize":
                result = {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "dsm-field-memory", "version": "0.1.0"},
                    "capabilities": {"tools": {}},
                }
            elif method == "notifications/initialized":
                return None
            elif method == "tools/list":
                result = {"tools": tools_schema()}
            elif method == "tools/call":
                params = request.get("params", {})
                result = self.call_tool(str(params.get("name")), dict(params.get("arguments", {})))
            else:
                return error_response(request_id, -32601, f"Unknown method: {method}")
            return {"jsonrpc": JSONRPC_VERSION, "id": request_id, "result": result}
        except Exception as exc:
            return error_response(request_id, -32000, str(exc))

    def _ensure_rld(self) -> Any:
        if self.rld is None:
            try:
                from rld import RecursiveLatentDNA
                self.rld = RecursiveLatentDNA(self.memory.storage.path.with_name("rld_genes.json"))
            except ImportError:
                raise ImportError("rld package is not available in the current environment")
        return self.rld

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "dsm_write":
            written = self.memory.write(
                str(arguments["text"]),
                category_path=arguments.get("category_path"),
                importance=float(arguments.get("importance", 0.5)),
                metadata=dict(arguments.get("metadata", {})),
            )
            self.memory.save()
            return text_result({"segment_ids": [segment.id for segment in written]})
        if name == "dsm_search":
            results = self.memory.route(str(arguments["query"]), k=int(arguments.get("k", 5)))
            return text_result(
                [
                    {
                        "id": item.segment.id,
                        "description": item.segment.description,
                        "text": item.segment.text,
                        "score": item.total_score,
                        "sparse_score": item.sparse_score,
                        "exact_matches": item.exact_matches,
                    }
                    for item in results
                ]
            )
        if name == "dsm_reason":
            trace = self.memory.reason(
                str(arguments["query"]),
                loops=int(arguments.get("loops", 3)),
                k=int(arguments.get("k", 5)),
            )
            return text_result(trace.to_dict() | {"context": trace.context.context_text})
        if name == "dsm_upsert_document":
            report = self.memory.upsert_document(
                str(arguments["document_id"]),
                str(arguments["text"]),
                category_path=arguments.get("category_path"),
                metadata=dict(arguments.get("metadata", {})),
            )
            self.memory.save()
            return text_result(report)
        if name == "dsm_graph":
            return text_result(graph_data(self.memory))
        if name == "rld_observe":
            rld_instance = self._ensure_rld()
            trajectory = rld_instance.observe(
                str(arguments["task"]),
                states=[str(item) for item in arguments.get("states", [])],
                actions=[str(item) for item in arguments.get("actions", [])],
                final_answer=str(arguments.get("final_answer", "")),
                success=bool(arguments.get("success", True)),
                utility=float(arguments.get("utility", 0.7)),
                tools_used=[str(item) for item in arguments.get("tools_used", [])],
                metadata=dict(arguments.get("metadata", {})),
            )
            rld_instance.save()
            return text_result({"trajectory_id": trajectory.id, **rld_instance.stats()})
        if name == "rld_activate":
            rld_instance = self._ensure_rld()
            context = rld_instance.active_context(
                str(arguments["query"]),
                threshold=optional_float(arguments.get("threshold")),
                top_k=optional_int(arguments.get("top_k")),
            )
            return text_result(
                {
                    "gene_ids": context.gene_ids,
                    "context": context.context_text,
                    "activated": [
                        {
                            "id": item.gene.id,
                            "probability": item.probability,
                            "weight": item.weight,
                            "reasons": item.reasons,
                        }
                        for item in context.activated
                    ],
                }
            )
        if name == "rld_consolidate":
            rld_instance = self._ensure_rld()
            report = rld_instance.consolidate(
                min_value=float(arguments.get("min_value", 0.18)),
                merge_similarity=float(arguments.get("merge_similarity", 0.74)),
                stabilize_reuse=int(arguments.get("stabilize_reuse", 3)),
            )
            rld_instance.save()
            return text_result(report.to_dict())
        if name == "rld_schema":
            rld_instance = self._ensure_rld()
            from rld import GENE_SCHEMA

            return text_result(GENE_SCHEMA)
        raise ValueError(f"Unknown tool: {name}")


def tools_schema() -> list[dict[str, Any]]:
    return [
        {
            "name": "dsm_write",
            "description": "Write a memory segment into DSM.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "category_path": {"type": "string"},
                    "importance": {"type": "number"},
                    "metadata": {"type": "object"},
                },
                "required": ["text"],
            },
        },
        {
            "name": "dsm_search",
            "description": "Hybrid dense+sparse search over DSM memory.",
            "inputSchema": {
                "type": "object",
                "properties": {"query": {"type": "string"}, "k": {"type": "integer"}},
                "required": ["query"],
            },
        },
        {
            "name": "dsm_reason",
            "description": "Run multi-hop reasoning loops over DSM memory.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "loops": {"type": "integer"},
                    "k": {"type": "integer"},
                },
                "required": ["query"],
            },
        },
        {
            "name": "dsm_upsert_document",
            "description": "Incrementally index only changed document chunks.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "document_id": {"type": "string"},
                    "text": {"type": "string"},
                    "category_path": {"type": "string"},
                    "metadata": {"type": "object"},
                },
                "required": ["document_id", "text"],
            },
        },
        {
            "name": "dsm_graph",
            "description": "Return graph visualization data for DSM memory.",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "rld_observe",
            "description": "Convert a reasoning trajectory into an RLD reasoning gene.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task": {"type": "string"},
                    "states": {"type": "array", "items": {"type": "string"}},
                    "actions": {"type": "array", "items": {"type": "string"}},
                    "final_answer": {"type": "string"},
                    "success": {"type": "boolean"},
                    "utility": {"type": "number"},
                    "tools_used": {"type": "array", "items": {"type": "string"}},
                    "metadata": {"type": "object"},
                },
                "required": ["task"],
            },
        },
        {
            "name": "rld_activate",
            "description": "Activate sparse Top-k RLD genes for the current query.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "top_k": {"type": "integer"},
                    "threshold": {"type": "number"},
                },
                "required": ["query"],
            },
        },
        {
            "name": "rld_consolidate",
            "description": "Run the RLD sleep phase: prune, merge and stabilize genes.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "min_value": {"type": "number"},
                    "merge_similarity": {"type": "number"},
                    "stabilize_reuse": {"type": "integer"},
                },
            },
        },
        {
            "name": "rld_schema",
            "description": "Return the formal JSON schema for RLD reasoning genes.",
            "inputSchema": {"type": "object", "properties": {}},
        },
    ]


def text_result(payload: Any) -> dict[str, Any]:
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(payload, ensure_ascii=False, indent=2),
            }
        ]
    }


def error_response(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": JSONRPC_VERSION, "id": request_id, "error": {"code": code, "message": message}}


def optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage", default=".dsm/memory.json")
    args = parser.parse_args()
    DsmMcpServer(DynamicSegmentedMemory(Path(args.storage))).serve()


if __name__ == "__main__":
    main()
