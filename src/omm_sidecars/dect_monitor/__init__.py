"""dect-monitor sidecar.

Prometheus exporter for DECT system health metrics.
Subscribes to OMM events and exposes gauges via HTTP.
"""

import asyncio
import logging
import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from prometheus_client import start_http_server

from mitel_ommclient2.client import OMMClient2

from omm_sidecars.dect_monitor import (
    pp_summary,
    rfp_media_stream_quality,
    rfp_state,
    rfp_stats,
)

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO").upper())
log = logging.getLogger(__name__)


async def _run() -> None:
    host = os.environ["OMM_HOST"]
    user = os.environ["OMM_USER"]
    password = os.environ["OMM_PASS"]
    prom_port = int(os.environ.get("OMM_PROM_PORT", "8000"))

    async with OMMClient2(host, user, password) as client:
        log.info("connected to %s, prometheus on :%d", host, prom_port)
        start_http_server(prom_port)

        async with asyncio.TaskGroup() as tg:
            await pp_summary.run(client, tg)
            await rfp_state.run(client, tg)
            await rfp_stats.run(client, tg)
            await rfp_media_stream_quality.run(client, tg)


def main() -> None:
    """Entry point for dect-monitor."""
    asyncio.run(_run())
