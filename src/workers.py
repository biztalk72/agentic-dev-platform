"""Agent workers: each is a thin LLM-calling loop with a fixed toolset."""
import json
from pathlib import Path
from src.graph_store import GraphStore
from src.vlm_client import VLMClient

OUT = Path("output")
OUT.mkdir(exist_ok=True)


class CollectorWorker:
    def __init__(self, store: GraphStore, vlm: VLMClient):
        self.store = store
        self.vlm = vlm

    async def run(self, task_id: int, intent: str):
        # Ingest structured log
        aid = self.store.add_asset("service", "demo-api", None, {"lang": "python", "framework": "fastapi"})
        self.store.add_exploration(task_id, "fact", "sample log: 3 errors on /login endpoint, 401 responses", None, "yields", aid)
        self.store.add_exploration(task_id, "fact", "sample log: mobile viewport width 375px triggers layout shift", None, "yields", aid)
        # VLM frame summary -> hint nodes
        for summary in self.vlm.summarize_clip(Path("sample_clip.mp4")):
            self.store.add_exploration(task_id, "hint", json.dumps(summary), None, "yields", aid)
        self.store.log("collector", "ingested", {"task_id": task_id, "assets": 1, "facts": 2, "hints": 1})


class PRDWorker:
    def __init__(self, store: GraphStore):
        self.store = store

    async def run(self, task_id: int, intent: str):
        graph = self.store.get_task_graph(task_id)
        facts = [g["content"] for g in graph if g["node_type"] == "fact"]
        hints = [g["content"] for g in graph if g["node_type"] == "hint"]
        prd = f"""# PRD Draft (auto-generated)

## Problem
Login errors on mobile viewport.

## Observed Facts
{chr(10).join('- ' + f for f in facts)}

## UI Hints (from VLM)
{chr(10).join('- ' + h for h in hints)}

## Requirements
- Fix disabled submit button on mobile viewport
- Resolve 401 errors on /login
- Stabilize layout shift at 375px width
"""
        (OUT / "PRD.md").write_text(prd)
        aid = self.store.add_asset("doc", "PRD.md", None, {"path": str(OUT / "PRD.md")})
        self.store.add_exploration(task_id, "finding", f"PRD drafted at {OUT / 'PRD.md'}", None, "yields", aid)
        self.store.log("prd", "wrote", {"task_id": task_id, "path": str(OUT / "PRD.md")})


class ReviewerWorker:
    def __init__(self, store: GraphStore):
        self.store = store

    async def run(self, task_id: int, intent: str):
        graph = self.store.get_task_graph(task_id)
        findings = [g for g in graph if g["node_type"] == "finding"]
        prd_finding = [f for f in findings if "PRD" in f["content"]]
        orphans = [f for f in findings if "PRD" not in f["content"]]
        status = "PASS" if prd_finding and not orphans else "FAIL"
        self.store.add_exploration(
            task_id, "finding",
            f"lineage-check: {status} - {len(prd_finding)} PRD-backed findings, {len(orphans)} orphan findings",
            None, "proves", None,
        )
        self.store.log("reviewer", "checked", {"task_id": task_id, "status": status, "orphans": len(orphans)})
        if status == "PASS":
            self.store.archive_exploration(task_id)
            self.store.complete_task(task_id)
            self.store.log("archive-policy", "archived", {"task_id": task_id})
