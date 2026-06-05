"""OMM sidecar entry point.

Connects to OMM, logs the version, and pings.
"""
import asyncio
import logging
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv is a dev-only dep; in prod it's not installed and
    # we expect env vars to be provided by the deployment environment.
    pass

from mitel_ommclient2.client import OMMClient2

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


async def _main() -> None:
    host = os.environ["OMM_HOST"]
    user = os.environ.get("OMM_USER", "admin")
    password = os.environ["OMM_PASS"]

    async with OMMClient2(host, user, password) as client:
        log.info("connected to OMM at %s", host)
        log.info("OMM version: %s", client.open_resp.ommVersion)
        if not await client.ping():
            raise RuntimeError("ping failed")
        log.info("ping ok")


def main() -> None:
    """Sync entry point."""
    asyncio.run(_main())


if __name__ == "__main__":
    main()
