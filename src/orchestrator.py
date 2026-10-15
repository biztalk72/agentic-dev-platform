"""Orchestrator: sole intent generator. Reads exploration graph, dispatches intents."""
import asyncio
from typing import Any

from .event_bus import Event, EventBus, EventType
from .graph_store import GraphStore
from .hitl_gate import GateRequest, HITLGate
from .workers import WORKERS


class Orchestrator:
    def __init__(self, store: GraphStore, bus: EventBus, gate: HITLGate):
        self.store = store
        self.bus = bus
        self.gate = gate
        bus subscribe if False else None  # placeholder to keep import order clean
        bus.subscribe(EventType.GRAPH_MUTATION, self._on_mutation)

    async def _on_mutation(self, event: Event):
        task_id = event.payload.get("task_id")
        if task_id is None:
            return
        intents = self.plan(task_id)
        for intent in intents:
            await self._dispatch(task_id, intent)

    def plan(self, task_id: int) -> list[dict]:
        """Read exploration graph + shared todo, emit intents in dependency order."""
        rows = self.store.get_explorations(task_id)
        has_fact = any(r["node_type"] == "fact" for r in rows)
        has_finding = any(r["node_type"] == "finding" for r in rows)
        has_prd = any(r["node_type"] == "finding" and "PRD" in r["content"] for r in rows)

        intents = []
        if not has_fact:
            intents.append({"worker": "collector", "intent": "ingest sample log + VLM frame summary", "op": "ingest"})
        if has_fact and not has_finding:
            intents.append({"worker": "prd", "intent": "draft PRD from collected facts", "op": "write_file"})
        if has_finding and not has_prd:
            intents.append({"worker": "reviewer", "intent": "lineage-check PRD against findings", "op": "review"})
        if has_prd:
            intents.append({"worker": "dashboard", "intent": "render project state from asset graph", "op": "render"})
        return intents

    async def _dispatch(self, task_id: int, intent: dict):
        op = intent.get("op", "")
        if self.gate.requires_gate(op):
            approved = await self.gate.ask(GateRequest(
                intent=intent["intent"], operation=op, task_id=task_id,
            ))
            if not approved:
                self.store.log("hitl", "denied", intent)
                return
        worker = WORKERS.get(intent["worker"])
        if not worker:
            self.store.log("orchestrator", "missing_worker", intent)
            return
        try:
            await worker.run(self.store, task_id, intent)
            await self.bus.publish(Event(EventType.GRAPH_MUTATION, {"task_id": task_id}))
        except Exception as e:
            self.store.log("orchestrator", "worker_error", {"intent": intent, "error": str(e)})
            await self.bus.publish(Event(EventType.WORKER_ERROR, {"task_id": task_id, "error": str(e)}))
