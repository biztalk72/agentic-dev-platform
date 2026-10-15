"""HITL gate: pauses tagged tool calls, prompts for approval, resumes on yes."""
import asyncio
from dataclasses import dataclass
from typing import Optional

from .event_bus import Event, EventBus, EventType


# Operations that require human approval (configurable per project)
DEFAULT_GATED_OPS = {"deploy", "schema_change", "payment_call", "auth_call"}


@dataclass
class GateRequest:
    intent: str
    operation: str
    task_id: int
    timeout_sec: int = 600  # 10 min default


class HITLGate:
    def __init__(self, bus: EventBus, gated_ops: Optional[set] = None):
        self.bus = bus
        self.gated_ops = gated_ops or DEFAULT_GATED_OPS
        self._pending: dict[int, asyncio.Future] = {}  # task_id -> Future[bool]
        bus.subscribe(EventType.GATE_RESPONSE, self._on_response)

    def requires_gate(self, operation: str) -> bool:
        return operation in self.gated_ops

    async def ask(self, req: GateRequest) -> bool:
        """Pause execution, prompt for approval, return True if approved."""
        loop = asyncio.get_running_loop()
        fut: asyncio.Future[bool] = loop.create_future()
        self._pending[req.task_id] = fut

        await self.bus.publish(Event(EventType.GATE_REQUEST, {
            "task_id": req.task_id,
            "intent": req.intent,
            "operation": req.operation,
        }))

        print(f"\n[GATE] Intent: {req.intent} (op={req.operation}). Approve? [y/N] ", end="", flush=True)
        try:
            approved = await asyncio.wait_for(fut, timeout=req.timeout_sec)
        except asyncio.TimeoutError:
            approved = False
            print("\n[GATE] Timeout -> denied, logged to audit.")
        finally:
            self._pending.pop(req.task_id, None)
        return approved

    def respond(self, task_id: int, approved: bool):
        """Called by CLI `approve` command or UI."""
        fut = self._pending.get(task_id)
        if fut and not fut.done():
            fut.set_result(approved)

    async def _on_response(self, event: Event):
        self.respond(event.payload["task_id"], bool(event.payload.get("approved")))
