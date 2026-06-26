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
from dataclasses import dataclass
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
class DeviceProperties:
    ipei: str
    name: str = ""
    encryption: bool = False

    @classmethod
    def from_json(cls, data: Any) -> "DeviceProperties":
        return cls(
            ipei=data["ipei"],
            name=data.get("name", ""),
            encryption=data.get("encryption", False),
        )


@dataclass
class DeviceConfig:
    currentNumber: int
    sipUsername: str
    properties: DeviceProperties

    @classmethod
    def from_json(cls, data: Any) -> "DeviceConfig":
        return cls(
            currentNumber=data["currentNumber"],
            sipUsername=data["sipUsername"],
            properties=DeviceProperties.from_json(data.get("properties", {})),
        )


async def pull_device_config(ipei: str) -> DeviceConfig:
    """Call SIP core API to get expected config for a DECT device."""
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
        return DeviceConfig.from_json(resp.json())


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

    # If swapping from old user, delete it (unbinds device)
    if old_uid:
        await client.delete_pp_user(uid=old_uid)
        await client.bind_user_device(new_uid, ppn)
    else:
        await client.bind_user_device(new_uid, ppn)

    return new_uid


async def reconcile_device(client: OMMClient2, config: DeviceConfig) -> None:
    """Reconcile OMM state with expected config from SIP core."""
    ipei = config.properties.ipei

    async with swap_lock:
        # Get device by IPEI
        try:
            resp = await client.get_pp_dev_by_ipei(ipei)
            dev = resp.pp[0]
        except Exception:
            log.warning("device not found for ipei=%s", ipei)
            return

        # Get current user state
        current_user: types.PPUserType | None = None
        if dev.uid is not None and dev.uid != 0:
            try:
                user_resp = await client.get_pp_user(dev.uid)
                current_user = user_resp.user[0]
            except Exception:
                pass

        # Swap user if number or SIP username changed
        needs_swap = (
            current_user is None
            or current_user.num != str(config.currentNumber)
            or current_user.sipAuthId != config.sipUsername
        )
        if needs_swap:
            new_user = types.PPUserType(
                num=str(config.currentNumber),
                name=config.properties.name,
                sipAuthId=config.sipUsername,
            )
            await set_device_user(
                client, dev.ppn, new_user, old_uid=dev.uid if dev.uid else None
            )
        else:
            # Same user, just update name
            assert current_user is not None
            await client.set_pp_user(
                types.PPUserType(uid=current_user.uid, name=config.properties.name)
            )

        # Always update device properties
        await client.set_pp_dev(
            types.PPDevType(ppn=dev.ppn, encrypt=config.properties.encryption)
        )

    log.info("reconciled ipei=%s ppn=%d num=%d", ipei, dev.ppn, config.currentNumber)


async def device_event_handler(client: OMMClient2) -> None:
    """Pull config from SIP core and reconcile for unbound devices."""
    log.info("subscribing to PPDevCnf")
    await client.subscribe(EventPPDevCnf, ppn=-1)

    async for event in client.events(EventPPCnf):
        if not event.pp:
            continue
        pp = event.pp[0]
        if pp.uid != 0:
            continue
        if not pp.ipei:
            log.warning("ppn %d has no IPEI, skipping", pp.ppn)
            continue

        try:
            config = await pull_device_config(pp.ipei)
            await reconcile_device(client, config)
        except Exception:
            log.exception("reconcile failed for ppn=%d", pp.ppn)


async def handle_webhook(client: OMMClient2, request: Request) -> JSONResponse:
    """Handle webhooks from the SIP core."""
    body = await request.json()
    event = body.get("event")

    log.info(
        "webhook %s: ipei=%s num=%s",
        event,
        body.get("properties", {}).get("ipei"),
        body.get("currentNumber"),
    )

    try:
        config = DeviceConfig.from_json(body)
        await reconcile_device(client, config)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

    return JSONResponse({"ok": True})


async def _main() -> None:
    """Entry point: connect and run sidecar tasks."""
    host = os.environ["OMM_HOST"]
    user = os.environ.get("OMM_USER", "admin")
    password = os.environ["OMM_PASS"]

    log.info("connecting to %s", host)
    async with OMMClient2(host, user, password, ommsync=True) as client:
        log.info("connected, version=%s", client.open_resp.ommVersion)

        async def reconcile_orphaned_devices() -> None:
            async for dev in client.pp_devs():
                if dev.uid == 0 and dev.ipei:
                    try:
                        config = await pull_device_config(dev.ipei)
                        await reconcile_device(client, config)
                    except Exception:
                        log.exception("startup reconcile failed for ppn=%d", dev.ppn)

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
            tg.create_task(reconcile_orphaned_devices())


def main() -> None:
    """Sync entry point."""
    asyncio.run(_main())
