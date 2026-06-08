"""dect-users sidecar.

Runs a keep-alive loop that ensures DECT subscription settings are correct:
auth code is "0000", auto-create is enabled, subscription mode is Configured.
Re-applies if changed externally (e.g. via web UI).

Also listens for PPDevCnf events and creates provisional users for unbound
devices with temp numbers in the 1905xxxx range.
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
from mitel_ommclient2.messages import EventPPCnf, EventPPDevCnf
from mitel_ommclient2 import types

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO").upper())
log = logging.getLogger(__name__)

SUBSCRIPTION_INTERVAL = 15  # seconds


def temp_number(ppn: int) -> str:
    """Provisional user number: 1905 + ppn zero-padded to 4 digits."""
    if ppn > 9999:
        raise ValueError(f"ppn {ppn} exceeds 1905xxxx range")
    return f"1905{ppn:04d}"


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


async def device_event_handler(client: OMMClient2) -> None:
    """Create provisional users for unbound devices."""
    log.info("subscribing to PPDevCnf")
    await client.subscribe(EventPPDevCnf, ppn=-1)

    async for event in client.events(EventPPCnf):
        if not event.pp:
            continue  # no device data in this event

        pp = event.pp[0]

        if pp.uid is None:
            continue
        if pp.uid != 0:
            continue  # already has a user

        try:
            num = temp_number(pp.ppn)
        except ValueError:
            log.error("ppn %d exceeds 1905xxxx range", pp.ppn)
            continue

        log.info("provisioning ppn=%d -> num=%s", pp.ppn, num)

        try:
            user = types.PPUserType(num=num)
            resp = await client.create_pp_user(user)
            new_uid = resp.user[0].uid
            log.info("created provisional user uid=%d num=%s", new_uid, num)

            await client.bind_user_device(new_uid, pp.ppn)
            log.info("bound uid=%d to ppn=%d", new_uid, pp.ppn)
        except Exception:
            log.exception("provisioning failed for ppn=%d", pp.ppn)


async def _main() -> None:
    """Entry point: connect and run sidecar tasks."""
    host = os.environ["OMM_HOST"]
    user = os.environ.get("OMM_USER", "admin")
    password = os.environ["OMM_PASS"]

    log.info("connecting to %s", host)
    async with OMMClient2(host, user, password, ommsync=True) as client:
        log.info("connected, version=%s", client.open_resp.ommVersion)
        async with asyncio.TaskGroup() as tg:
            tg.create_task(subscription_loop(client))
            tg.create_task(device_event_handler(client))


def main() -> None:
    """Sync entry point."""
    asyncio.run(_main())
