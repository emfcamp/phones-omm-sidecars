"""dect-users sidecar.

Runs a keep-alive loop that ensures DECT subscription settings are correct:
auth code is "0000", auto-create is enabled, subscription mode is Configured.
Re-applies if changed externally (e.g. via web UI).

Also listens for PPDevCnf events and creates provisional users for unbound
devices by calling the SIP core's temp number API.
"""

import asyncio
import logging
import os
from dataclasses import dataclass

import httpx

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


@dataclass
class TempNumberResult:
    tempNumber: int
    sipUsername: str


async def assign_temp_number(ipei: str) -> TempNumberResult:
    """Call SIP core API to assign a temp number for a DECT device."""
    api_url = os.environ["CORE_API_URL"]
    api_token = os.environ["CORE_API_TOKEN"]

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{api_url}/temp-numbers/assign/dect",
            headers={"Authorization": f"Bearer {api_token}"},
            json={"ipei": ipei},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return TempNumberResult(
            tempNumber=data["tempNumber"],
            sipUsername=data["sipUsername"],
        )


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

        if not pp.ipei:
            log.error("ppn %d has no IPEI, skipping", pp.ppn)
            continue

        try:
            result = await assign_temp_number(pp.ipei)
        except Exception:
            log.exception("failed to assign temp number for IPEI %s", pp.ipei)
            continue

        num = result.tempNumber
        sip_username = result.sipUsername

        log.info("provisioning ppn=%d -> num=%d sip=%s", pp.ppn, num, sip_username)

        try:
            user = types.PPUserType(num=str(num), sipAuthId=sip_username)
            resp = await client.create_pp_user(user)
            new_uid = resp.user[0].uid
            log.info("created provisional user uid=%d num=%d", new_uid, num)

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
