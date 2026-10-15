#!/usr/bin/env python3
"""Agentic Dev Platform MVP entrypoint: dual-graph loop + CLI demo + optional FastAPI."""
import asyncio
import json
import sys
from pathlib import Path

from src.event_bus import EventBus
from src.graph_store import GraphStore
from src.hitl_gate import HITLGate
from src.orchestrator import Orchestrator
from src.vlm_client import VLMClient
from src.workers import CollectorWorker, PRDWorker, ReviewerWorker


async def demo():
    store = GraphStore()
    bus = EventBus()
    gate = HITLGate(store, auto_approve_demo=True)
    vlm = VLMClient()
    collector = CollectorWorker(store, vlm)
    prd = PRDWorker(store)
    reviewer = ReviewerWorker(store)
    orch = Orchestrator(store, bus, gate, collector, prd, reviewer)

    print("=== Agentic Dev Platform Demo (Grok build) ===\n")
    task_id = await orch.run_task("Fix mobile login errors and layout shift")
    print(f"\nDemo complete. Task ID: {task_id}")
    print("Outputs:")
    print(" -", Path("output") / "PRD.md")
    print(" -", store.db_path)
    snap = store.dashboard_snapshot()
    print(json.dumps(snap, indent=2)[:800])
    # Write dashboard data for GitHub Pages
    Path("web/data.json").parent.mkdir(exist_ok=True)
    Path("web/data.json").write_text(json.dumps(snap, indent=2))
    print(" - web/data.json (dashboard snapshot)")


def main():
    if "--demo" in sys.argv:
        asyncio.run(demo())
    else:
        print("Usage: python3 -m src.main --demo")
        store = GraphStore()
        print("SQLite schema initialized at", store.db_path)


if __name__ == "__main__":
    main()
