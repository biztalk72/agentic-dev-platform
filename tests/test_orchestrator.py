# 오케스트레이터(intent 순서, 게이트 거부, E2E 완료·아카이브) 테스트
import asyncio

from src.event_bus import Event, EventBus, EventType
from src.graph_store import GraphStore
from src.hitl_gate import HITLGate
from src.orchestrator import Orchestrator


def make_orchestrator(tmp_path):
    store = GraphStore(tmp_path / "test.db")
    bus = EventBus()
    gate = HITLGate(bus)
    return Orchestrator(store, bus, gate), store, bus


def test_plan_starts_with_collector(tmp_path):
    orch, store, _ = make_orchestrator(tmp_path)
    task_id = store.create_task("goal")
    intents = orch.plan(task_id)
    assert [i["worker"] for i in intents] == ["collector"]


def test_plan_dispatches_analyst_after_facts(tmp_path):
    orch, store, _ = make_orchestrator(tmp_path)
    task_id = store.create_task("goal")
    store.add_exploration(task_id, "fact", "log: errors on /login", None, "yields", None)
    intents = orch.plan(task_id)
    assert [i["worker"] for i in intents] == ["analyst"]


def test_plan_dispatches_prd_after_analysis(tmp_path):
    orch, store, _ = make_orchestrator(tmp_path)
    task_id = store.create_task("goal")
    store.add_exploration(task_id, "fact", "log: errors", None, "yields", None)
    store.add_exploration(task_id, "finding", "analyst: defect likely", None, "yields", None)
    intents = orch.plan(task_id)
    assert [i["worker"] for i in intents] == ["prd"]


def test_plan_dispatches_reviewer_after_prd(tmp_path):
    orch, store, _ = make_orchestrator(tmp_path)
    task_id = store.create_task("goal")
    store.add_exploration(task_id, "fact", "log: errors", None, "yields", None)
    store.add_exploration(task_id, "finding", "analyst: defect likely", None, "yields", None)
    store.add_exploration(task_id, "finding", "PRD drafted at output/PRD.md", None, "yields", None)
    intents = orch.plan(task_id)
    assert [i["worker"] for i in intents] == ["reviewer"]


def test_plan_dispatches_dashboard_after_review(tmp_path):
    orch, store, _ = make_orchestrator(tmp_path)
    task_id = store.create_task("goal")
    store.add_exploration(task_id, "fact", "log: errors", None, "yields", None)
    store.add_exploration(task_id, "finding", "analyst: defect likely", None, "yields", None)
    store.add_exploration(task_id, "finding", "PRD drafted at output/PRD.md", None, "yields", None)
    store.add_exploration(task_id, "finding", "lineage-check: 1 orphan findings", None, "proves", None)
    intents = orch.plan(task_id)
    assert [i["worker"] for i in intents] == ["dashboard"]


def test_denied_gate_blocks_worker_and_logs(tmp_path):
    class DenyingGate:
        def requires_gate(self, operation):
            return operation == "deploy"

        async def ask(self, req):
            return False

    store = GraphStore(tmp_path / "test.db")
    bus = EventBus()
    orch = Orchestrator(store, bus, DenyingGate())
    task_id = store.create_task("goal")

    asyncio.run(orch._dispatch(task_id, {
        "worker": "dashboard", "intent": "deploy dashboard", "op": "deploy",
    }))

    assert store.has_log("hitl", "denied")
    assert not store.has_log("dashboard", "rendered")


def _run_loop(store):
    async def run():
        bus = EventBus()
        gate = HITLGate(bus)
        Orchestrator(store, bus, gate)
        bus_task = asyncio.create_task(bus.run())
        task_id = store.create_task("demo goal")
        await bus.publish(Event(EventType.GRAPH_MUTATION, {"task_id": task_id}))
        await asyncio.wait_for(bus._queue.join(), timeout=5)
        bus_task.cancel()
        try:
            await bus_task
        except asyncio.CancelledError:
            pass
        return task_id
    return asyncio.run(run())


def test_demo_loop_runs_all_workers_and_archives(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "output").mkdir()

    store = GraphStore(tmp_path / "test.db")
    task_id = _run_loop(store)

    task = store.get_task(task_id)
    assert task["status"] == "completed"
    assert task["completed_at"] is not None
    node_types = [r["node_type"] for r in store.get_explorations(task_id)]
    assert node_types.count("fact") == 1
    assert node_types.count("hint") == 1
    assert node_types.count("finding") == 3  # analyst, prd, reviewer
    for actor, action in [
        ("collector", "ingested"), ("analyst", "produced_finding"),
        ("prd", "wrote"), ("reviewer", "checked"), ("dashboard", "rendered"),
    ]:
        assert store.has_log(actor, action), f"{actor} did not run"
    archived = store.con.execute(
        "SELECT * FROM archived_explorations WHERE task_id=?", (task_id,)
    ).fetchall()
    assert len(archived) == 1
    assert (tmp_path / "output" / "PRD.md").exists()
    assert (tmp_path / "output" / "dashboard.md").exists()
    assert store.has_log("orchestrator", "task_completed")


def test_second_task_in_same_store_also_completes(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "output").mkdir()

    store = GraphStore(tmp_path / "test.db")
    first = _run_loop(store)
    second = _run_loop(store)

    assert store.get_task(first)["status"] == "completed"
    assert store.get_task(second)["status"] == "completed"
    assert store.has_log("dashboard", "rendered", first)
    assert store.has_log("dashboard", "rendered", second)
