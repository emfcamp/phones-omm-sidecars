"""dect-users sidecar.

Runs a keep-alive loop that ensures DECT subscription settings are correct:
auth code is "0000", auto-create is enabled, subscription mode is Configured.
Re-applies if changed externally (e.g. via web UI).

Also listens for PPDevCnf events and creates provisional users for unbound
devices by calling the SIP core's temp number API.

Exposes a webhook endpoint for the SIP core to notify us of bind/unbind events.
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from functools import partial
from typing import Any

import httpx
import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.middleware import Middleware
from starlette.routing import Route

from omm_sidecars._auth import BearerAuthMiddleware

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from mitel_ommclient2.client import OMMClient2
from mitel_ommclient2.messages import EventPPCnf, EventPPDevCnf
from mitel_ommclient2 import types

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
)
log = logging.getLogger(__name__)

SUBSCRIPTION_INTERVAL = 15  # seconds

# Protects the unbind/bind critical section. The event handler re-checks
# device state inside this lock to ignore intermediate states (uid=0) that
# occur between unbind and bind during a webhook swap.
swap_lock = asyncio.Lock()


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
class WebhookProperties:
    name: str = ""
    encryption: bool = False


@dataclass
class WebhookBody:
    event: str
    vanityNumber: int
    tempNumber: int
    properties: WebhookProperties = field(default_factory=WebhookProperties)

    @classmethod
    def from_json(cls, data: Any) -> "WebhookBody":
        return cls(
            event=data["event"],
            vanityNumber=data["vanityNumber"],
            tempNumber=data["tempNumber"],
            properties=WebhookProperties(**data.get("properties", {})),
        )


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


async def set_device_user(
    client: OMMClient2,
    ppn: int,
    new_user: types.PPUserType,
    old_uid: int | None = None,
) -> int:
    """Create a user and bind to a device. If old_uid is given, delete it first (swap)."""
    assert new_user.num is not None

    # Delete stale user with same number if it exists
    try:
        resp = await client.get_pp_user_by_number(new_user.num)
        await client.delete_pp_user(uid=resp.user[0].uid)
    except Exception:
        pass

    # Create new user
    resp = await client.create_pp_user(new_user)
    new_uid = resp.user[0].uid
    log.info("created user uid=%d num=%s", new_uid, new_user.num)

    # If swapping from old user, delete it (unbinds device) in lock
    if old_uid:
        async with swap_lock:
            await client.delete_pp_user(uid=old_uid)
            await client.bind_user_device(new_uid, ppn)
    else:
        await client.bind_user_device(new_uid, ppn)

    return new_uid


async def provision_device(client: OMMClient2, ppn: int) -> None:
    """Assign a temp number and bind to a device."""
    # Re-check device state inside lock to ignore intermediate states
    async with swap_lock:
        resp = await client.get_pp_dev(ppn)
        pp = resp.pp[0]

    if pp.uid != 0:
        log.debug("ppn %d already has user uid=%d, skipping", ppn, pp.uid)
        return
    if not pp.ipei:
        log.warning("ppn %d has no IPEI, skipping", ppn)
        return

    result = await assign_temp_number(pp.ipei)

    user = types.PPUserType(num=str(result.tempNumber), sipAuthId=result.sipUsername)
    await set_device_user(client, ppn, user)
    log.info("provisioned ppn=%d -> num=%d", ppn, result.tempNumber)


async def device_event_handler(client: OMMClient2) -> None:
    """Create provisional users for unbound devices."""
    log.info("subscribing to PPDevCnf")
    await client.subscribe(EventPPDevCnf, ppn=-1)

    async for event in client.events(EventPPCnf):
        if not event.pp:
            continue
        pp = event.pp[0]
        if pp.uid != 0:
            continue

        try:
            await provision_device(client, pp.ppn)
        except Exception:
            log.exception("provisioning failed for ppn=%d", pp.ppn)


async def apply_dev_properties(
    client: OMMClient2,
    ppn: int,
    properties: WebhookProperties,
) -> None:
    """Apply device properties."""
    pp = types.PPDevType(ppn=ppn, encrypt=properties.encryption)
    await client.set_pp_dev(pp)


async def update_properties(
    client: OMMClient2,
    vanity: int,
    properties: WebhookProperties,
) -> None:
    """Update user and device properties for a vanity number."""
    resp = await client.get_pp_user_by_number(str(vanity))
    user = resp.user[0]
    if user.ppn is None:
        raise ValueError(f"user {vanity} has no ppn")

    await client.set_pp_user(types.PPUserType(uid=user.uid, name=properties.name))
    await apply_dev_properties(client, user.ppn, properties)


async def move_user(
    client: OMMClient2,
    old_num: int,
    new_num: int,
    new_properties: WebhookProperties,
) -> None:
    """Move a user from old_num to new_num with the given properties."""
    resp = await client.get_pp_user_by_number(str(old_num))
    old_user = resp.user[0]
    if old_user.ppn is None:
        raise ValueError(f"user {old_num} has no ppn")

    new_user = types.PPUserType(num=str(new_num), name=new_properties.name)
    await set_device_user(client, old_user.ppn, new_user, old_uid=old_user.uid)

    await apply_dev_properties(client, old_user.ppn, new_properties)


async def handle_webhook(client: OMMClient2, request: Request) -> JSONResponse:
    """Handle bind/unbind webhooks from the SIP core."""
    body = WebhookBody.from_json(await request.json())

    log.info(
        "webhook %s: temp=%d vanity=%d", body.event, body.tempNumber, body.vanityNumber
    )

    try:
        match body.event:
            case "bind":
                await move_user(
                    client, body.tempNumber, body.vanityNumber, body.properties
                )
            case "unbind":
                await move_user(
                    client, body.vanityNumber, body.tempNumber, WebhookProperties()
                )
            case "properties":
                await update_properties(client, body.vanityNumber, body.properties)
            case _:
                return JSONResponse(
                    {"error": f"unknown event: {body.event}"}, status_code=400
                )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=404)

    return JSONResponse({"ok": True})


async def _main() -> None:
    """Entry point: connect and run sidecar tasks."""
    host = os.environ["OMM_HOST"]
    user = os.environ.get("OMM_USER", "admin")
    password = os.environ["OMM_PASS"]

    log.info("connecting to %s", host)
    async with OMMClient2(host, user, password, ommsync=True) as client:
        log.info("connected, version=%s", client.open_resp.ommVersion)

        async def provision_orphaned_devices() -> None:
            async for dev in client.pp_devs():
                if dev.uid == 0:
                    try:
                        await provision_device(client, dev.ppn)
                    except Exception:
                        log.exception("startup provisioning failed for ppn=%d", dev.ppn)

        app = Starlette(
            routes=[
                Route("/webhook", partial(handle_webhook, client), methods=["POST"]),
            ],
            middleware=[Middleware(BearerAuthMiddleware)],
        )

        port = int(os.environ.get("HTTP_PORT", "8080"))
        config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
        server = uvicorn.Server(config)

        async with asyncio.TaskGroup() as tg:
            tg.create_task(subscription_loop(client))
            tg.create_task(device_event_handler(client))
            tg.create_task(server.serve())
            tg.create_task(provision_orphaned_devices())


def main() -> None:
    """Sync entry point."""
    asyncio.run(_main())
