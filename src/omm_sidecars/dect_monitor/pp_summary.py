"""PP summary collector.

Subscribes to EventPPDevSummary and EventPPUserSummary.
Polls initial state, then listens for updates.
Exposes device and user counts as Prometheus gauges.
"""

import asyncio
import logging
from typing import Protocol

from prometheus_client import Gauge

from mitel_ommclient2.client import OMMClient2
from mitel_ommclient2.messages import EventPPDevSummary, EventPPUserSummary

from omm_sidecars.dect_monitor._util import listen

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


async def run(client: OMMClient2, tg: asyncio.TaskGroup) -> None:
    """Subscribe, poll initial state, register listeners."""
    await client.subscribe(EventPPDevSummary)
    await client.subscribe(EventPPUserSummary)
    log.info("subscribed to PPDevSummary, PPUserSummary")

    # initial poll
    dev = await client.get_pp_dev_summary()
    await _update_dev(dev)
    user = await client.get_pp_user_summary()
    await _update_user(user)
    log.info(
        "initial state: %d devices (%d subscribed), %d users (%d sip, %d locatable)",
        dev.nRecords or 0,
        dev.subscribedDevs or 0,
        user.nRecords or 0,
        user.nSipRegistration or 0,
        user.nLocatable or 0,
    )

    # register listeners
    tg.create_task(listen(client, EventPPDevSummary, _update_dev))
    tg.create_task(listen(client, EventPPUserSummary, _update_user))


async def _update_dev(event: _HasDevSummary) -> None:
    if event.nRecords is not None:
        pp_dev_total.set(event.nRecords)
    if event.subscribedDevs is not None:
        pp_dev_subscribed.set(event.subscribedDevs)


async def _update_user(event: _HasUserSummary) -> None:
    if event.nRecords is not None:
        pp_user_total.set(event.nRecords)
    if event.nLocatable is not None:
        pp_user_locatable.set(event.nLocatable)
    if event.nSipRegistration is not None:
        pp_user_sip_registered.set(event.nSipRegistration)
