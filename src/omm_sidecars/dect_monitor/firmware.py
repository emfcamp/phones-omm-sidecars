"""Firmware overview collector.

Subscribes to EventPPFirmwareUpdateOverview.
Polls initial state, then listens for updates.
Exposes firmware download counts as Prometheus gauges.
"""

import asyncio
import logging
from typing import Protocol

from prometheus_client import Gauge

from mitel_ommclient2.client import OMMClient2
from mitel_ommclient2.messages import EventPPFirmwareUpdateOverview

from omm_sidecars.dect_monitor._util import listen

log = logging.getLogger(__name__)


# -- protocols --


class _HasFirmwareOverview(Protocol):
    state: str | None
    known: int | None
    ready: int | None
    pending: int | None
    active: int | None
    barred: int | None
    errored: int | None
    notReachable: int | None
    detached: int | None
    version: str | None


# -- prometheus gauges --

_STATE_MAP = {"startup": 0, "disabled": 1, "running": 2, "error": 3}

fw_overview_state = Gauge(
    "dect_firmware_overview_state",
    "Firmware download manager state (0=startup, 1=disabled, 2=running, 3=error)",
)
fw_overview_count = Gauge(
    "dect_firmware_overview_count",
    "Firmware download phone count by status",
    ["status"],
)


async def run(client: OMMClient2, tg: asyncio.TaskGroup) -> None:
    """Subscribe, poll initial state, register listeners."""
    await client.subscribe(EventPPFirmwareUpdateOverview)
    log.info("subscribed to PPFirmwareUpdateOverview")

    # initial poll
    overview = await client.get_pp_firmware_update_overview()
    await _update_gauges(overview)
    log.info(
        "initial firmware overview: state=%s active=%s pending=%s ready=%s errored=%s",
        overview.state,
        overview.active,
        overview.pending,
        overview.ready,
        overview.errored,
    )

    # register listener
    tg.create_task(listen(client, EventPPFirmwareUpdateOverview, _update_gauges))


async def _update_gauges(event: _HasFirmwareOverview) -> None:
    if event.state is not None:
        fw_overview_state.set(_STATE_MAP.get(event.state, -1))
    for status in (
        "known",
        "ready",
        "pending",
        "active",
        "barred",
        "errored",
        "notReachable",
        "detached",
    ):
        value = getattr(event, status, None)
        if value is not None:
            fw_overview_count.labels(status).set(value)
