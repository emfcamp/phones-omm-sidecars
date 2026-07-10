"""RFP sync quality collector.

Subscribes to EventRFPSyncQuality.
Polls initial state, then listens for updates.
Exposes per-RFP sync quality gauges.
"""

import asyncio
import logging

from prometheus_client import Gauge

from mitel_ommclient2.client import OMMClient2
from mitel_ommclient2.messages import EventRFPSyncQuality, EventRFPState
from mitel_ommclient2.types import SyncQualityType

from omm_sidecars.dect_monitor._util import listen

log = logging.getLogger(__name__)

# -- prometheus gauges --

sync_strong_rels = Gauge(
    "dect_rfp_sync_strong_rels",
    "Sync relations with RSSI > -73 dBm",
    ["rfp_id"],
)
sync_low_rels = Gauge(
    "dect_rfp_sync_low_rels",
    "Sync relations with RSSI < -73 dBm",
    ["rfp_id"],
)
sync_max_rssi = Gauge(
    "dect_rfp_sync_max_rssi_dbm",
    "Max RSSI of strong relations (dBm)",
    ["rfp_id"],
)
sync_min_rssi = Gauge(
    "dect_rfp_sync_min_rssi_dbm",
    "Min RSSI of low relations (dBm)",
    ["rfp_id"],
)


async def run(client: OMMClient2, tg: asyncio.TaskGroup) -> None:
    """Subscribe, poll initial state, register listener."""
    await client.subscribe(EventRFPSyncQuality, rfpId=-1)
    log.info("subscribed to RFPSyncQuality")

    # initial poll
    async for sq in client.rfp_sync_quality():
        _update_gauges(sq)
    log.info("initial state: sync quality loaded")

    tg.create_task(listen(client, EventRFPSyncQuality, _on_event))
    tg.create_task(listen(client, EventRFPState, _on_state_event))


async def _on_event(event: EventRFPSyncQuality) -> None:
    for sq in event.syncQuality:
        _update_gauges(sq)


async def _on_state_event(event: EventRFPState) -> None:
    for rfp in event.rfp:
        if rfp.connected is False:
            _reset_gauges(str(rfp.id))


def _reset_gauges(rfp_id: str) -> None:
    """Reset all sync quality gauges on disconnect."""
    sync_strong_rels.labels(rfp_id).set(0)
    sync_low_rels.labels(rfp_id).set(0)
    sync_max_rssi.labels(rfp_id).set(0)
    sync_min_rssi.labels(rfp_id).set(0)


def _update_gauges(sq: SyncQualityType) -> None:
    rfp_id = str(sq.id)
    if sq.strongRels is not None:
        sync_strong_rels.labels(rfp_id).set(sq.strongRels)
    if sq.lowRels is not None:
        sync_low_rels.labels(rfp_id).set(sq.lowRels)
    if sq.maxRSSI is not None:
        sync_max_rssi.labels(rfp_id).set(sq.maxRSSI)
    if sq.minRSSI is not None:
        sync_min_rssi.labels(rfp_id).set(sq.minRSSI)
