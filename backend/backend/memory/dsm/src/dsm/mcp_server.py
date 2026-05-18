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

    def __init__(self, memory: DynamicSegmentedMemory):
        self.memory = memory

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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage", default=".dsm/memory.json")
    args = parser.parse_args()
    DsmMcpServer(DynamicSegmentedMemory(Path(args.storage))).serve()


if __name__ == "__main__":
    main()
