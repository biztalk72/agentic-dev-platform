"""MVP entrypoint: event-driven dual-graph loop with real workers."""
import asyncio
import sys
from pathlib import Path

from .event_bus import Event, EventBus, EventType
from .graph_store import GraphStore
from .hitl_gate import HITLGate
from .orchestrator import Orchestrator


async def demo(store: GraphStore, bus: EventBus, orch: Orchestrator):
    # start bus loop in background
    bus_task = asyncio.create_task(bus.run())

    task_id = store.create_task("demo goal: mobile login defect -> PRD + review + dashboard")
    store.log("orchestrator", "started", {"task_id": task_id})

    # seed: kick off with a graph mutation (empty exploration -> collector)
    await bus.publish(Event(EventType.GRAPH_MUTATION, {"task_id": task_id}))

    # let the loop run for a bit
    await asyncio.sleep(2)

    task = store.get_task(task_id)
    print("\nDemo complete.")
    print(" - task:", task)
    print(" - assets:", store.query_assets())
    print(" - explorations:", len(store.get_explorations(task_id)))
    for r in store.get_explorations(task_id):
        print(f"   ({r['node_type']}) {r['content']}")
    print(" - outputs: output/PRD.md, output/dashboard.md, agentic.db")

    bus_task.cancel()
    try:
        await bus_task
    except asyncio.CancelledError:
        pass


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
