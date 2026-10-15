"""Asyncio event bus: graph mutations wake the orchestrator."""
import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable


class EventType(str, Enum):
    GRAPH_MUTATION = "GRAPH_MUTATION"
    TASK_COMPLETED = "TASK_COMPLETED"
    GATE_REQUEST = "GATE_REQUEST"
    GATE_RESPONSE = "GATE_RESPONSE"
    WORKER_ERROR = "WORKER_ERROR"


@dataclass
class Event:
    type: EventType
    payload: dict = field(default_factory=dict)


class EventBus:
    def __init__(self):
        self._queue: asyncio.Queue[Event] = asyncio.Queue()
        self._handlers: dict[EventType, list[Callable[[Event], Awaitable[None]]]] = {
            t: [] for t in EventType
        }

    def subscribe(self, event_type: EventType, handler: Callable[[Event], Awaitable[None]]):
        self._handlers[event_type].append(handler)

    async def publish(self, event: Event):
        await self._queue.put(event)

    async def run(self):
        """Main loop: drain queue and dispatch to handlers."""
        while True:
            event = await self._queue.get()
            for handler in self._handlers.get(event.type, []):
                try:
                    await handler(event)
                except Exception as e:
                    # fail loud: record error event rather than swallowing
                    await self._queue.put(Event(EventType.WORKER_ERROR, {"error": str(e), "source": repr(handler)}))
            self._queue.task_done()
