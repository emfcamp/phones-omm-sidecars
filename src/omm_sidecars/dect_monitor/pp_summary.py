"""PP summary collector.

Subscribes to EventPPDevSummary and EventPPUserSummary.
Polls initial state, then listens for updates.
Exposes device and user counts as Prometheus gauges.
"""

import asyncio
import logging
from collections.abc import Callable
from typing import Protocol, TypeVar

from prometheus_client import Gauge

from mitel_ommclient2.client import OMMClient2
from mitel_ommclient2.messages import Event, EventPPDevSummary, EventPPUserSummary

EventT = TypeVar("EventT", bound=Event)

log = logging.getLogger(__name__)


# -- protocols for shared fields between response and event types --


class _HasDevSummary(Protocol):
    nRecords: int | None
    subscribedDevs: int | None


class _HasUserSummary(Protocol):
    nRecords: int | None
    nLocatable: int | None
    nSipRegistration: int | None


# -- prometheus gauges --

pp_dev_total = Gauge("dect_pp_dev_total", "Total DECT phone devices configured")
pp_dev_subscribed = Gauge(
    "dect_pp_dev_subscribed", "DECT phone devices with confirmed subscription"
)
pp_user_total = Gauge("dect_pp_user_total", "Total DECT phone users configured")
pp_user_locatable = Gauge(
    "dect_pp_user_locatable", "DECT phone users with locatable=True"
)
pp_user_sip_registered = Gauge(
    "dect_pp_user_sip_registered", "DECT phone users with active SIP registration"
)


async def run(client: OMMClient2) -> None:
    """Subscribe, poll initial state, listen for updates."""
    await client.subscribe(EventPPDevSummary)
    await client.subscribe(EventPPUserSummary)
    log.info("subscribed to PPDevSummary, PPUserSummary")

    # initial poll
    dev = await client.get_pp_dev_summary()
    _update_dev(dev)
    user = await client.get_pp_user_summary()
    _update_user(user)
    log.info(
        "initial state: %d devices (%d subscribed), %d users (%d sip, %d locatable)",
        dev.nRecords or 0,
        dev.subscribedDevs or 0,
        user.nRecords or 0,
        user.nSipRegistration or 0,
        user.nLocatable or 0,
    )

    # listen for updates
    await asyncio.gather(
        _listen(client, EventPPDevSummary, _update_dev),
        _listen(client, EventPPUserSummary, _update_user),
    )


async def _listen(
    client: OMMClient2, event_cls: type[EventT], handler: Callable[[EventT], None]
) -> None:
    async for event in client.events(event_cls):
        handler(event)


def _update_dev(event: _HasDevSummary) -> None:
    if event.nRecords is not None:
        pp_dev_total.set(event.nRecords)
    if event.subscribedDevs is not None:
        pp_dev_subscribed.set(event.subscribedDevs)


def _update_user(event: _HasUserSummary) -> None:
    if event.nRecords is not None:
        pp_user_total.set(event.nRecords)
    if event.nLocatable is not None:
        pp_user_locatable.set(event.nLocatable)
    if event.nSipRegistration is not None:
        pp_user_sip_registered.set(event.nSipRegistration)
