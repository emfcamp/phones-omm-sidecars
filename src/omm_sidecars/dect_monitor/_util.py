"""Shared helpers for dect-monitor collectors."""

from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

from mitel_ommclient2.client import OMMClient2
from mitel_ommclient2.messages import Event

EventT = TypeVar("EventT", bound=Event)
Handler = Callable[[EventT], Coroutine[Any, Any, None]]


async def listen(
    client: OMMClient2, event_cls: type[EventT], handler: Handler[EventT]
) -> None:
    """Subscribe to events and call handler for each one."""
    async for event in client.events(event_cls):
        await handler(event)
