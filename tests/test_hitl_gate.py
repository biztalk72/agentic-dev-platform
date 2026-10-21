# HITL 게이트(게이트 대상 판정, 승인, 거부, 타임아웃) 단위 테스트
import asyncio

from src.event_bus import Event, EventBus, EventType
from src.hitl_gate import GateRequest, HITLGate


def test_requires_gate_only_for_gated_ops():
    gate = HITLGate(EventBus())
    assert gate.requires_gate("deploy")
    assert gate.requires_gate("schema_change")
    assert not gate.requires_gate("ingest")
    assert not gate.requires_gate("render")


def _ask(gate, task_id, approved, timeout_sec=5):
    async def run():
        ask_task = asyncio.create_task(gate.ask(GateRequest(
            intent="demo", operation="deploy", task_id=task_id, timeout_sec=timeout_sec,
        )))
        await asyncio.sleep(0)
        gate.respond(task_id, approved)
        return await ask_task
    return asyncio.run(run())


def test_ask_returns_true_on_approval():
    gate = HITLGate(EventBus())
    assert _ask(gate, 1, approved=True) is True


def test_ask_returns_false_on_denial():
    gate = HITLGate(EventBus())
    assert _ask(gate, 2, approved=False) is False


def test_ask_times_out_to_denied():
    async def run():
        gate = HITLGate(EventBus())
        return await gate.ask(GateRequest(
            intent="demo", operation="deploy", task_id=3, timeout_sec=0,
        ))
    assert asyncio.run(run()) is False


def test_gate_response_event_resolves_ask():
    async def run():
        bus = EventBus()
        gate = HITLGate(bus)
        bus_task = asyncio.create_task(bus.run())
        ask_task = asyncio.create_task(gate.ask(GateRequest(
            intent="demo", operation="deploy", task_id=4, timeout_sec=5,
        )))
        await asyncio.sleep(0)
        await bus.publish(Event(EventType.GATE_RESPONSE, {"task_id": 4, "approved": True}))
        result = await ask_task
        bus_task.cancel()
        try:
            await bus_task
        except asyncio.CancelledError:
            pass
        return result
    assert asyncio.run(run()) is True
