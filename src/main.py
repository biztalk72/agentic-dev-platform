"""MVP entrypoint: event-driven dual-graph loop with real workers."""
import asyncio
import json
import sys
from pathlib import Path

from .event_bus import Event, EventBus, EventType
from .graph_store import GraphStore
from .hitl_gate import HITLGate
from .orchestrator import Orchestrator

ROOT = Path(__file__).resolve().parents[1]


def write_web_snapshot(store: GraphStore) -> Path:
    path = ROOT / "web" / "data.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(store.snapshot(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


async def demo(store: GraphStore, bus: EventBus, orch: Orchestrator):
    bus_task = asyncio.create_task(bus.run())
    timed_out = False

    task_id = store.create_task("demo goal: mobile login defect -> PRD + review + dashboard")
    store.log("orchestrator", "started", {"task_id": task_id})
    await bus.publish(Event(EventType.GRAPH_MUTATION, {"task_id": task_id}))
    try:
        await asyncio.wait_for(bus._queue.join(), timeout=5)
    except asyncio.TimeoutError:
        timed_out = True

    snapshot_path = write_web_snapshot(store)
    task = store.get_task(task_id)
    print("\nDemo complete.")
    print(" - task:", task)
    print(" - assets:", store.query_assets())
    print(" - explorations:", len(store.get_explorations(task_id)))
    for row in store.get_explorations(task_id):
        print(f"   ({row['node_type']}) {row['content']}")
    print(" - outputs: output/PRD.md, output/dashboard.md, agentic.db")
    print(" - web:", snapshot_path)

    bus_task.cancel()
    try:
        await bus_task
    except asyncio.CancelledError:
        pass
    if timed_out:
        raise SystemExit("demo did not finish within 5s")


async def main():
    store = GraphStore()
    bus = EventBus()
    gate = HITLGate(bus)
    orch = Orchestrator(store, bus, gate)
    if "--demo" in sys.argv:
        await demo(store, bus, orch)
    else:
        print("Usage: python3 -m src.main --demo")
        print("SQLite schema initialized at", store.db_path)


if __name__ == "__main__":
    asyncio.run(main())
