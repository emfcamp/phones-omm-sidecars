"""dect-users sidecar.

Runs a keep-alive loop that ensures DECT subscription settings are correct:
auth code is "0000", auto-create is enabled, subscription mode is Configured.
Re-applies if changed externally (e.g. via web UI).
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

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

SUBSCRIPTION_INTERVAL = 15  # seconds


async def subscription_loop(client: OMMClient2) -> None:
    """Keep-alive: ensure auth code, auto-create, and subscription mode are correct."""
    log.info("subscription loop started")

    while True:
        try:
            if await client.get_dect_auth_code() != "0000":
                log.info("resetting auth code to 0000")
                await client.set_dect_auth_code("0000")

            if not await client.get_dev_auto_create():
                log.info("enabling device auto-create")
                await client.set_dev_auto_create(True)

            mode = await client.get_dect_subscription_mode()
            if str(mode) != "Configured":
                log.info("setting subscription mode: %s -> Configured", mode)
                await client.set_dect_subscription_mode("Configured")

        except Exception:
            log.exception("subscription loop iteration failed")

        await asyncio.sleep(SUBSCRIPTION_INTERVAL)


async def _main() -> None:
    """Entry point: connect and run sidecar tasks."""
    host = os.environ["OMM_HOST"]
    user = os.environ.get("OMM_USER", "admin")
    password = os.environ["OMM_PASS"]

    log.info("connecting to %s", host)
    async with OMMClient2(host, user, password, ommsync=True) as client:
        log.info("connected, version=%s", client.open_resp.ommVersion)
        await subscription_loop(client)


def main() -> None:
    """Sync entry point."""
    asyncio.run(_main())
