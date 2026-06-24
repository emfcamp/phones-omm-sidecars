"""RFP statistics collector.

Polls GetRFPStatisticConfig once at startup to discover counter names.
Polls GetRFPStatistic every 60s to read cumulative counters per RFP.
Exposes one Prometheus Gauge per counter type, labeled by RFP.
"""

import asyncio
import logging
import re

from prometheus_client import Gauge

from mitel_ommclient2.client import OMMClient2

log = logging.getLogger(__name__)

POLL_INTERVAL = 60  # seconds

# populated at startup from GetRFPStatisticConfig
_gauges: dict[int, Gauge] = {}
_name_map: dict[int, str] = {}


def _sanitize(name: str) -> str:
    """Sanitize counter name for use as Prometheus metric name suffix."""
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = s.strip("_")
    return s


async def run(client: OMMClient2, tg: asyncio.TaskGroup) -> None:
    """Fetch config, create gauges, start poll loop."""
    config = await client.get_rfp_statistic_config()
    head = config.rfpStatHead[0]
    log.info(
        "rfp stats config: %d counters, %d record sets, resolution=%s",
        head.numElemPerRec,
        head.recordSets,
        head.resolution,
    )

    for stat_name in config.rfpStatName:
        _name_map[stat_name.elemId] = stat_name.name
        metric_name = (
            f"dect_rfp_stat_{_sanitize(stat_name.group)}_{_sanitize(stat_name.name)}"
        )
        _gauges[stat_name.elemId] = Gauge(
            metric_name,
            f"{stat_name.group}: {stat_name.name}",
            ["rfp_id"],
        )
        log.info("  %d: %s -> %s", stat_name.elemId, stat_name.name, metric_name)

    tg.create_task(_poll_loop(client))


async def _poll_loop(client: OMMClient2) -> None:
    """Poll RFP statistics every POLL_INTERVAL seconds."""
    while True:
        await _poll(client)
        await asyncio.sleep(POLL_INTERVAL)


async def _poll(client: OMMClient2) -> None:
    """Fetch all RFP statistic counters and update gauges."""
    async for stat in client.rfp_statistics(record_set=0):
        rfp_id = str(stat.id)
        values = stat.counter.split(",")
        for elem_id, value_str in enumerate(values):
            if elem_id in _gauges:
                try:
                    _gauges[elem_id].labels(rfp_id).set(int(value_str))
                except ValueError:
                    log.warning(
                        "non-numeric counter value: rfp=%d elem=%d value=%r",
                        stat.id,
                        elem_id,
                        value_str,
                    )
