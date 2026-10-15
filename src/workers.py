"""Worker roles: Collector, Analyst, PRD, Reviewer, Dashboard."""
import json
from pathlib import Path
from typing import Protocol

from .graph_store import GraphStore

OUT = Path("output")
OUT.mkdir(exist_ok=True)


class Worker(Protocol):
    async def run(self, store: GraphStore, task_id: int, intent: dict) -> None: ...


class CollectorWorker:
    """Ingests logs and VLM frame summaries into fact/hint nodes."""
    async def run(self, store: GraphStore, task_id: int, intent: dict):
        # demo: synthetic log + VLM summary
        aid = store.add_asset("service", "demo-api", None, {"lang": "python"})
        store.add_exploration(task_id, "fact", "sample log: 3 errors on /login", None, "yields", aid)
        store.add_exploration(task_id, "hint", "VLM: submit button disabled on mobile", None, "yields", aid)
        store.log("collector", "ingested", {"assets": 1, "facts": 1, "hints": 1})


class AnalystWorker:
    """Cross-references facts, produces findings."""
    async def run(self, store: GraphStore, task_id: int, intent: dict):
        rows = store.get_explorations(task_id)
        facts = [r for r in rows if r["node_type"] == "fact"]
        hints = [r for r in rows if r["node_type"] == "hint"]
        finding = f"analyst: {len(facts)} facts, {len(hints)} hints -> mobile login defect likely"
        store.add_exploration(task_id, "finding", finding, None, "yields", None)
        store.log("analyst", "produced_finding", {"finding": finding})


class PRDWorker:
    """Reads requirements, drafts/updates PRD."""
    async def run(self, store: GraphStore, task_id: int, intent: dict):
        rows = store.get_explorations(task_id)
        facts = [r["content"] for r in rows if r["node_type"] == "fact"]
        hints = [r["content"] for r in rows if r["node_type"] == "hint"]
        prd = (
            "# Demo PRD\n\n## Problem\n"
            + "\n".join(f"- {f}" for f in facts)
            + "\n\n## UI Observations\n"
            + "\n".join(f"- {h}" for h in hints)
            + "\n\n## Requirements\n- Fix disabled submit button on mobile viewport.\n"
        )
        (OUT / "PRD.md").write_text(prd)
        aid = store.add_asset("doc", "PRD.md", None, {"path": str(OUT / "PRD.md")})
        store.add_exploration(task_id, "finding", f"PRD drafted at output/PRD.md", None, "yields", aid)
        store.log("prd", "wrote", {"path": str(OUT / "PRD.md")})


class ReviewerWorker:
    """Re-reads PRD against findings, emits feedback as new intents."""
    async def run(self, store: GraphStore, task_id: int, intent: dict):
        rows = store.get_explorations(task_id)
        orphans = [r["content"] for r in rows if r["node_type"] == "finding" and "PRD" not in r["content"]]
        store.add_exploration(
            task_id, "finding",
            f"lineage-check: {len(orphans)} orphan findings",
            None, "proves", None,
        )
        store.log("reviewer", "checked", {"orphans": len(orphans)})


class DashboardWorker:
    """Renders project state from the asset graph."""
    async def run(self, store: GraphStore, task_id: int, intent: dict):
        assets = store.query_assets()
        lines = ["# Dashboard Snapshot", "", f"Task {task_id} assets:"]
        for a in assets:
            lines.append(f"- [{a['type']}] {a['name']}")
        lines.append("")
        lines.append("Explorations:")
        for r in store.get_explorations(task_id):
            lines.append(f"- ({r['node_type']}) {r['content']}")
        (OUT / "dashboard.md").write_text("\n".join(lines))
        store.log("dashboard", "rendered", {"path": str(OUT / "dashboard.md")})


WORKERS: dict[str, Worker] = {
    "collector": CollectorWorker(),
    "analyst": AnalystWorker(),
    "prd": PRDWorker(),
    "reviewer": ReviewerWorker(),
    "dashboard": DashboardWorker(),
}
