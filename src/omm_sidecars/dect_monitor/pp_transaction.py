"""PPTransaction collector.

Subscribes to EventPPTransaction.
Counts transactions by type per RFP.
Events without rfpId use label "none".
Tracks new device registrations.
"""

import asyncio
import logging

from prometheus_client import Counter, Gauge

from mitel_ommclient2.client import OMMClient2
from mitel_ommclient2.messages import EventPPTransaction

from omm_sidecars.dect_monitor._util import listen

log = logging.getLogger(__name__)

# -- prometheus metrics --

pp_transaction_total = Counter(
    "dect_pp_transaction_total",
    "PPTransaction events by type and RFP",
    ["rfp_id", "tr_type"],
)
new_device_count = Gauge(
    "dect_new_device_count",
    "New DECT devices seen (first event from unknown ppn)",
    ["rfp_id"],
)

_known_ppns: set[int] = set()


async def run(client: OMMClient2, tg: asyncio.TaskGroup) -> None:
    """Subscribe, enumerate known PPNs, register listener."""
    async for pp in client.pp_devs():
        _known_ppns.add(pp.ppn)
    log.info("known ppns: %d devices", len(_known_ppns))

    await client.subscribe(EventPPTransaction, ppn=-1)
    log.info("subscribed to PPTransaction")

    tg.create_task(listen(client, EventPPTransaction, _on_event))


async def _on_event(event: EventPPTransaction) -> None:
    rfp_id = str(event.rfpId) if event.rfpId is not None else "none"
    tr_type = event.trType or "unknown"
    pp_transaction_total.labels(rfp_id, tr_type).inc()
    log.debug(
        "PPTransaction: ppn=%s trType=%s rfpId=%s", event.ppn, event.trType, event.rfpId
    )

    if event.ppn is not None and event.ppn not in _known_ppns:
        _known_ppns.add(event.ppn)
        new_device_count.labels(rfp_id).inc()
        if tr_type != "LocReg":
            log.warning("new ppn %d first seen as %s, not LocReg", event.ppn, tr_type)
        else:
            log.info("new device: ppn=%d via LocReg on rfp %s", event.ppn, rfp_id)
