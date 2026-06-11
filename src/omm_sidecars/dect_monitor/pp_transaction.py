"""PPTransaction collector.

Subscribes to EventPPTransaction.
Counts transactions by type per RFP.
Events without rfpId use label "none".
"""

import asyncio
import logging

from prometheus_client import Counter

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


async def run(client: OMMClient2, tg: asyncio.TaskGroup) -> None:
    """Subscribe and register listener."""
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
