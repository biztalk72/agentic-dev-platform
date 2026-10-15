"""Orchestrator: sole intent generator. Reads exploration graph, dispatches intents in dependency order."""
from src.graph_store import GraphStore
from src.hitl_gate import HITLGate
from src.workers import CollectorWorker, PRDWorker, ReviewerWorker
from src.event_bus import Event, EventBus


class Orchestrator:
    def __init__(self, store: GraphStore, bus: EventBus, gate: HITLGate,
                 collector: CollectorWorker, prd: PRDWorker, reviewer: ReviewerWorker):
        self.store = store
        self.bus = bus
        self.gate = gate
        self.workers = {"collector": collector, "prd": prd, "reviewer": reviewer}

    def plan(self, task_id: int) -> list[dict]:
        """Fixed 3-step chain for demo; real version reads graph state + shared todo."""
        return [
            {"step": 1, "worker": "collector", "intent": "ingest sample log + VLM frame summary"},
            {"step": 2, "worker": "prd", "intent": "draft PRD from collected facts and hints"},
            {"step": 3, "worker": "reviewer", "intent": "lineage-check PRD against findings", "gate": False},
        ]

    async def run_task(self, goal: str) -> int:
        task_id = self.store.create_task(goal)
        self.store.log("orchestrator", "started", {"task_id": task_id, "goal": goal})
        await self.bus emit(Event("GRAPH_MUTATION", {"task_id": task_id, "reason": "task_created"}))
        for step in self.plan(task_id):
            if step.get("gate") and self.gate.requires_gate(step["intent"]):
                ok = await self.gate.ask(step["intent"])
                if not ok:
                    self.store.log("hitl", "denied", step)
                    continue
            worker = self.workers[step["worker"]]
            await worker.run(task_id, step["intent"])
            await self.bus emit(Event("GRAPH_MUTATION", {"task_id": task_id, "reason": f"step_{step['step']}_done"}))
        return task_id
