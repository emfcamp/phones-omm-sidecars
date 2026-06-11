"""RFP IP quality collector.

Subscribes to EventRFPIpQuality.
Polls initial state, then listens for updates.
Exposes per-RFP IP quality metrics.
"""

import asyncio
import logging

from prometheus_client import Gauge

from mitel_ommclient2.client import OMMClient2
from mitel_ommclient2.messages import EventRFPIpQuality
from mitel_ommclient2.types import IpQualityType

from omm_sidecars.dect_monitor._util import listen

log = logging.getLogger(__name__)

# RTT bucket boundaries in ms (from SIP-DECT OM System Manual).
# OMM returns raw interval counts; we convert to cumulative buckets
# for Prometheus histogram format.
_RTT_BOUNDS_MS = (25, 50, 150, 500)

# -- prometheus gauges --

ip_connected_time = Gauge(
    "dect_rfp_ip_connected_time_seconds",
    "Time RFP connected to OMM (seconds)",
    ["rfp_id"],
)
ip_current_rtt = Gauge(
    "dect_rfp_ip_current_rtt_us", "Current round trip time (µs)", ["rfp_id"]
)
ip_max_rtt = Gauge("dect_rfp_ip_max_rtt_us", "Highest RTT measured (µs)", ["rfp_id"])
ip_rtt_sample_count = Gauge(
    "dect_rfp_ip_rtt_sample_count",
    "Number of RTT samples acquired",
    ["rfp_id"],
)
ip_rtt_bucket = Gauge(
    "dect_rfp_ip_rtt_bucket",
    "RTT samples by latency bucket (cumulative)",
    ["rfp_id", "le"],
)


async def run(client: OMMClient2, tg: asyncio.TaskGroup) -> None:
    """Subscribe, poll initial state, register listener."""
    await client.subscribe(EventRFPIpQuality, rfpId=-1)
    log.info("subscribed to RFPIpQuality")

    # initial poll
    async for iq in client.rfp_ip_quality():
        _update_gauges(iq)
    log.info("initial state: IP quality loaded")

    tg.create_task(listen(client, EventRFPIpQuality, _on_event))


async def _on_event(event: EventRFPIpQuality) -> None:
    for iq in event.ipQuality:
        _update_gauges(iq)


def _update_gauges(iq: IpQualityType) -> None:
    rfp_id = str(iq.id)
    if iq.connectedTime is not None:
        ip_connected_time.labels(rfp_id).set(iq.connectedTime)
    if iq.currentRTT is not None:
        ip_current_rtt.labels(rfp_id).set(iq.currentRTT)
    if iq.maxRTT is not None:
        ip_max_rtt.labels(rfp_id).set(iq.maxRTT)
    if iq.count is not None:
        ip_rtt_sample_count.labels(rfp_id).set(iq.count)

    # Convert raw interval counts to cumulative histogram buckets.
    # OMM intervals: 1=<25ms, 2=25-50ms, 3=50-150ms, 4=150-500ms, 5=>=500ms
    intervals = [
        iq.interval1 or 0,
        iq.interval2 or 0,
        iq.interval3 or 0,
        iq.interval4 or 0,
        iq.interval5 or 0,
    ]
    cumulative = 0
    for bound, count in zip(_RTT_BOUNDS_MS, intervals):
        cumulative += count
        ip_rtt_bucket.labels(rfp_id, str(bound)).set(cumulative)
    # +Inf bucket = total
    ip_rtt_bucket.labels(rfp_id, "+Inf").set(cumulative + intervals[4])
