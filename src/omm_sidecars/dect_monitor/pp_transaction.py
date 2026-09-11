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
from functools import partial

from prometheus_client import Counter, Gauge
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from mitel_ommclient2.client import OMMClient2
from mitel_ommclient2.messages import EventPPTransaction

from omm_sidecars.dect_monitor import rfp_state
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
rfp_active_call_legs = Gauge(
    "dect_rfp_active_call_legs",
    "Active DECT call legs per RFP",
    ["rfp_id"],
)
pp_active_1h = Gauge(
    "dect_pp_active_1h",
    "PPs with activity in the last hour",
)

# -- sqlite --


def _init_db() -> sqlite3.Connection:
    db_path = os.path.join(os.environ.get("DATA_DIR", "/data"), "pp_transactions.db")
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
_current_rfp: dict[int, int] = {}  # ppn → rfp_id
_active_ppns: dict[int, float] = {}  # ppn → last event timestamp


async def _handle_location(client: OMMClient2, request: Request) -> JSONResponse:
    num = request.query_params.get("num")
    if not num:
        return JSONResponse({"error": "missing num parameter"}, status_code=400)

    try:
        resp = await client.get_pp_user_by_number(num)
    except Exception as e:
        return JSONResponse({"error": f"{type(e).__name__}: {e}"}, status_code=404)

    if not resp.user:
        return JSONResponse({"error": "no user found"}, status_code=404)

    ppn = resp.user[0].ppn
    if ppn == 0:
        return JSONResponse({"error": "user is unbound (no device)"}, status_code=404)
    row = _db.execute(
        "SELECT tr_type, rfp_id, ts FROM pp_transaction WHERE ppn = ? AND rfp_id IS NOT NULL ORDER BY ts DESC LIMIT 1",
        (ppn,),
    ).fetchone()
    if row is None:
        return JSONResponse({"ppn": ppn, "error": "no transactions"}, status_code=404)

    tr_type, rfp_id, ts = row
    rfp_name = (
        rfp_state.rfp_names.get(rfp_id, "unknown") if rfp_id is not None else None
    )
    return JSONResponse(
        {
            "ppn": ppn,
            "num": num,
            "rfp_id": rfp_id,
            "rfp_name": rfp_name,
            "last_event": tr_type,
            "timestamp": ts,
        }
    )


async def run(client: OMMClient2, app: Starlette, tg: asyncio.TaskGroup) -> None:
    """Subscribe, enumerate known PPNs, register listener, add HTTP route."""
    async for pp in client.pp_devs():
        _known_ppns.add(pp.ppn)
    log.info("known ppns: %d devices", len(_known_ppns))

    await client.subscribe(EventPPTransaction, ppn=-1)
    log.info("subscribed to PPTransaction")

    tg.create_task(listen(client, EventPPTransaction, _on_event))
    tg.create_task(_poll_call_state(client))

    app.routes.append(Route("/location", partial(_handle_location, client)))


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

    _active_ppns[event.ppn] = time.time()
    cutoff = time.time() - 3600
    stale = [ppn for ppn, ts in _active_ppns.items() if ts < cutoff]
    for ppn in stale:
        del _active_ppns[ppn]
    pp_active_1h.set(len(_active_ppns))

    _update_call_legs(event.ppn, event.trType, event.rfpId)


def _update_call_legs(ppn: int, tr_type: str, rfp_id: int | None) -> None:
    if tr_type == "Establish" and rfp_id is not None:
        old_rfp = _current_rfp.get(ppn)
        if old_rfp is not None:
            _bump_call_legs(old_rfp, -1)
        _current_rfp[ppn] = rfp_id
        _bump_call_legs(rfp_id, 1)
    elif tr_type == "ConnHandover" and rfp_id is not None:
        old_rfp = _current_rfp.get(ppn)
        if old_rfp is not None:
            _bump_call_legs(old_rfp, -1)
            _current_rfp[ppn] = rfp_id
            _bump_call_legs(rfp_id, 1)
    elif tr_type in ("Release", "Detach"):
        old_rfp = _current_rfp.pop(ppn, None)
        if old_rfp is not None:
            _bump_call_legs(old_rfp, -1)


def _bump_call_legs(rfp_id: int, delta: int) -> None:
    key = str(rfp_id)
    cur = _active_call_legs.get(key, 0) + delta
    if cur < 0:
        log.warning("active call legs would go negative on rfp %d", rfp_id)
        cur = 0
    _active_call_legs[key] = cur
    rfp_active_call_legs.labels(key).set(cur)


_active_call_legs: dict[str, int] = {}


async def _poll_call_state(client: OMMClient2) -> None:
    """Periodically check call state for PPs with active call legs."""
    while True:
        await asyncio.sleep(60)
        for ppn in list(_current_rfp.keys()):
            try:
                resp = await client.get_pp_state(ppn)
            except Exception:
                log.warning("GetPPState failed for ppn=%d", ppn, exc_info=True)
                continue
            if resp.callState is not None and resp.callState.value in ("idle", "none"):
                old_rfp = _current_rfp.pop(ppn, None)
                if old_rfp is not None:
                    _bump_call_legs(old_rfp, -1)
                    log.warning(
                        "phantom call leg: ppn=%d rfp=%d callState=%s",
                        ppn, old_rfp, resp.callState,
                    )
