"""dect-fun sidecar.

Fun DECT integrations for EMFcamp.
Messaging bridge between DECT phones and the SIP core.
"""

import asyncio
import logging
import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from mitel_ommclient2.client import OMMClient2

from omm_sidecars.dect_fun import messaging

logging.basicConfig(
    format="%(levelname)s %(name)s %(message)s",
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
)
log = logging.getLogger(__name__)


async def _run() -> None:
    host = os.environ["OMM_HOST"]
    user = os.environ["OMM_USER"]
    password = os.environ["OMM_PASS"]

    async with OMMClient2(host, user, password) as client:
        log.info("connected to %s", host)

        async with asyncio.TaskGroup() as tg:
            await messaging.start(client, tg)
            log.info("messaging bridge started")


def main() -> None:
    """Entry point for dect-fun."""
    asyncio.run(_run())
