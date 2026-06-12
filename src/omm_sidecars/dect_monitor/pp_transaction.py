"""PPTransaction collector.

Subscribes to EventPPTransaction.
Counts transactions by type per RFP.
Events without rfpId use label "none".
Tracks new device registrations.
Logs all events to SQLite in DATA_DIR.
"""

import asyncio
import logging
import os
import sqlite3
import time

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

# -- sqlite --


def _init_db() -> sqlite3.Connection:
    db_path = os.path.join(os.environ["DATA_DIR"], "pp_transactions.db")
    log.info("opening sqlite db at %s", db_path)
    db = sqlite3.connect(db_path)
    db.execute("""
        CREATE TABLE IF NOT EXISTS pp_transaction (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts REAL NOT NULL,
            ppn INTEGER,
            tr_type TEXT,
            rfp_id INTEGER
        )
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_ts ON pp_transaction (ts)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_ppn ON pp_transaction (ppn)")
    db.commit()
    return db


_db = _init_db()

# -- state --

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
    assert event.ppn is not None, "ppn is mandatory"
    assert event.trType is not None, "trType is mandatory"

    log.debug(
        "PPTransaction: ppn=%s trType=%s rfpId=%s", event.ppn, event.trType, event.rfpId
    )

    prom_rfp_id = str(event.rfpId) if event.rfpId is not None else "none"
    pp_transaction_total.labels(prom_rfp_id, event.trType).inc()

    if event.ppn not in _known_ppns:
        _known_ppns.add(event.ppn)
        new_device_count.labels(prom_rfp_id).inc()
        if event.trType != "LocReg":
            log.warning(
                "new ppn %d first seen as %s, not LocReg", event.ppn, event.trType
            )
        else:
            log.info("new device: ppn=%d via LocReg on rfp %s", event.ppn, event.rfpId)

    _db.execute(
        "INSERT INTO pp_transaction (ts, ppn, tr_type, rfp_id) VALUES (?, ?, ?, ?)",
        (time.time(), event.ppn, event.trType, event.rfpId),
    )
    _db.commit()
