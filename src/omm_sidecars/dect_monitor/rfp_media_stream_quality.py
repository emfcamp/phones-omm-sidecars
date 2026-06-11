"""RFP media stream quality collector.

Subscribes to EventRFPMediaStreamQuality.
Polls initial state, then listens for updates.
Exposes per-RFP media stream quality gauges.
"""

import asyncio
import logging

from prometheus_client import Gauge

from mitel_ommclient2.client import OMMClient2
from mitel_ommclient2.messages import EventRFPMediaStreamQuality, EventRFPMsQuality
from mitel_ommclient2.types import MsQualityType

from omm_sidecars.dect_monitor._util import listen

log = logging.getLogger(__name__)

# -- prometheus gauges --

ms_connects = Gauge("dect_rfp_ms_connects", "Audio connections served", ["rfp_id"])
ms_duration = Gauge(
    "dect_rfp_ms_duration", "Audio connection duration sum (seconds)", ["rfp_id"]
)
ms_packets_rx = Gauge("dect_rfp_ms_packets_rx", "RTP packets received", ["rfp_id"])
ms_octets_rx = Gauge("dect_rfp_ms_octets_rx", "Audio octets received", ["rfp_id"])
ms_packets_tx = Gauge("dect_rfp_ms_packets_tx", "RTP packets sent", ["rfp_id"])
ms_octets_tx = Gauge("dect_rfp_ms_octets_tx", "Audio octets sent", ["rfp_id"])
ms_packets_lost = Gauge(
    "dect_rfp_ms_packets_lost", "Percent of packets lost", ["rfp_id"]
)
ms_max_jitter = Gauge("dect_rfp_ms_max_jitter", "Jitter (ms)", ["rfp_id"])


async def run(client: OMMClient2, tg: asyncio.TaskGroup) -> None:
    """Subscribe, poll initial state, register listener."""
    await client.subscribe(EventRFPMsQuality, rfpId=-1)
    log.info("subscribed to RFPMsQuality")

    # initial poll
    async for ms in client.rfp_media_stream_quality():
        _update_gauges(ms)
    log.info("initial state: media stream quality loaded")

    tg.create_task(listen(client, EventRFPMediaStreamQuality, _on_event))


async def _on_event(event: EventRFPMediaStreamQuality) -> None:
    for ms in event.msQuality:
        _update_gauges(ms)


def _update_gauges(ms: MsQualityType) -> None:
    rfp_id = str(ms.id)
    if ms.connects is not None:
        ms_connects.labels(rfp_id).set(ms.connects)
    if ms.duration is not None:
        ms_duration.labels(rfp_id).set(ms.duration)
    if ms.packetsRx is not None:
        ms_packets_rx.labels(rfp_id).set(ms.packetsRx)
    if ms.octetsRx is not None:
        ms_octets_rx.labels(rfp_id).set(ms.octetsRx)
    if ms.packetsTx is not None:
        ms_packets_tx.labels(rfp_id).set(ms.packetsTx)
    if ms.octetsTx is not None:
        ms_octets_tx.labels(rfp_id).set(ms.octetsTx)
    if ms.packetsLost is not None:
        ms_packets_lost.labels(rfp_id).set(ms.packetsLost)
    if ms.maxJitter is not None:
        ms_max_jitter.labels(rfp_id).set(ms.maxJitter)
