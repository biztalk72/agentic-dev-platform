"""Async event bus for graph mutations."""
import asyncio
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Event:
    type: str
    payload: dict[str, Any] = field(default_factory=dict)


class EventBus:
    def __init__(self):
        self._queue: asyncio.Queue[Event] = asyncio.Queue()

    async def emit(self, event: Event):
        await self._queue.put(event)

    async def get(self) -> Event:
        return await self._queue.get()

    def emit_nowait(self, event: Event):
        self._queue.put_nowait(event)
