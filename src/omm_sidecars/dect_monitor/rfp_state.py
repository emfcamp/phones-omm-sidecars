"""RFP state collector.

Subscribes to EventRFPState and EventRFPCnf.
Re-polls RFP on any event to get full state.
Exposes per-RFP gauges with labels.
"""

import asyncio
import logging
from functools import partial
from typing import Protocol

from prometheus_client import Gauge

from mitel_ommclient2.client import OMMClient2
from mitel_ommclient2.messages import EventRFPCnf, EventRFPState
from mitel_ommclient2.types import RFPType

from omm_sidecars.dect_monitor._util import listen

log = logging.getLogger(__name__)


class _HasRFPList(Protocol):
    rfp: list[RFPType]


_SYNC_STATE_MAP = {"Inactive": 0, "NotSynced": 1, "Searching": 2, "Synced": 3}

# -- shared state --
rfp_names: dict[int, str] = {}

# -- prometheus gauges --

rfp_info = Gauge("dect_rfp_info", "RFP metadata", ["rfp_id", "rfp_name"])
rfp_connected = Gauge("dect_rfp_connected", "RFP connected state", ["rfp_id"])
rfp_dect_running = Gauge("dect_rfp_dect_running", "RFP DECT running state", ["rfp_id"])
rfp_sync_state = Gauge(
    "dect_rfp_sync_state",
    "RFP sync state (0=Inactive, 1=NotSynced, 2=Searching, 3=Synced)",
    ["rfp_id"],
)
rfp_sync_rels = Gauge(
    "dect_rfp_sync_relations", "Number of RFP sync relations", ["rfp_id"]
)
rfp_encryption_active = Gauge(
    "dect_rfp_encryption_active", "RFP DECT encryption active", ["rfp_id"]
)
rfp_version_mismatch = Gauge(
    "dect_rfp_version_mismatch",
    "RFP software version mismatch with OMM",
    ["rfp_id"],
)


async def run(client: OMMClient2, tg: asyncio.TaskGroup) -> None:
    """Subscribe, register listeners and initial poll."""
    await client.subscribe(EventRFPState, rfpId=-1)
    await client.subscribe(EventRFPCnf, rfpId=-1)
    log.info("subscribed to RFPState, RFPCnf")

    on_event = partial(_on_rfp_event, client)
    tg.create_task(listen(client, EventRFPState, on_event))
    tg.create_task(listen(client, EventRFPCnf, on_event))
    tg.create_task(_initial_poll(client))


async def _on_rfp_event(client: OMMClient2, event: _HasRFPList) -> None:
    for rfp in event.rfp:
        rfp_data = (await client.get_rfp(rfp.id, with_state=True)).rfp[0]
        _update_gauges(rfp_data)


async def _initial_poll(client: OMMClient2) -> None:
    async for rfp in client.rfps(with_state=True):
        _update_gauges(rfp)
    log.info("initial state: RFPs loaded")


def _update_gauges(rfp: RFPType) -> None:
    rfp_id = str(rfp.id)
    old_name = rfp_names.get(rfp.id)
    if old_name is not None and old_name != rfp.name:
        rfp_info.remove(rfp_id, old_name)
    rfp_names[rfp.id] = rfp.name
    rfp_info.labels(rfp_id, rfp.name).set(1)
    rfp_connected.labels(rfp_id).set(int(rfp.connected or False))
    rfp_dect_running.labels(rfp_id).set(int(rfp.dectRunning or False))
    if rfp.syncState is not None:
        rfp_sync_state.labels(rfp_id).set(_SYNC_STATE_MAP.get(str(rfp.syncState), -1))
    if rfp.nSyncRels is not None:
        rfp_sync_rels.labels(rfp_id).set(rfp.nSyncRels)
    if rfp.encryptionActive is not None:
        rfp_encryption_active.labels(rfp_id).set(int(rfp.encryptionActive))
    if rfp.versionMismatch is not None:
        rfp_version_mismatch.labels(rfp_id).set(int(rfp.versionMismatch))
