"""Messaging bridge between DECT phones and the SIP core.

Inbound: SIP core POSTs to us, we deliver to DECT via AXI SendMessage.
Outbound: DECT phones send messages (EventMessageSend), we POST to SIP core.
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from functools import partial

import httpx
import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from mitel_ommclient2.client import OMMClient2
from mitel_ommclient2.messages import EventMessageSend, SendMessage
from mitel_ommclient2.types import MessageType

log = logging.getLogger(__name__)


# -- HTTP body types --


@dataclass
class MessageBody:
    to: int
    fromNumber: int
    content: str
    fromName: str | None = None


# -- inbound: core → DECT --


async def _handle_inbound(client: OMMClient2, request: Request) -> JSONResponse:
    """Receive a message from the SIP core and deliver to a DECT phone."""
    body = MessageBody(**await request.json())

    msg = MessageType(
        sendTime=int(time.time()),
        toAddr=f"tel:{body.to}",
        fromAddr=f"tel:{body.fromNumber}",
        fromName=body.fromName,
        content=body.content,
        priority="Normal",
    )

    try:
        await client.request(SendMessage(msg=[msg]))
    except Exception as e:
        log.error("inbound failed: %d → %d: %s", body.fromNumber, body.to, e)
        return JSONResponse({"error": str(e)}, status_code=500)

    log.info("inbound: %d → %d", body.fromNumber, body.to)
    return JSONResponse({"status": "ok"})


# -- outbound: DECT → core --


async def _relay_outbound(msg: MessageType) -> None:
    """Forward a single DECT-originated message to the SIP core."""
    core_url = os.environ["MESSAGE_TARGET_URL"]

    to = int(msg.toAddr.lower().removeprefix("tel:"))
    from_number = int(msg.fromAddr.lower().removeprefix("tel:"))

    body = MessageBody(
        to=to,
        fromNumber=from_number,
        fromName=msg.fromName,
        content=msg.content or "",
    )

    token = os.environ["MESSAGE_TARGET_TOKEN"]
    async with httpx.AsyncClient() as http:
        resp = await http.post(
            core_url,
            json=body.__dict__,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        resp.raise_for_status()
        log.info("outbound: %d → %d", from_number, to)


async def _listen_outbound(client: OMMClient2) -> None:
    """Subscribe to EventMessageSend and relay each one to the core."""
    await client.subscribe(EventMessageSend, ppn=-1)
    log.info("subscribed to EventMessageSend")

    async for event in client.events(EventMessageSend):
        for msg in event.msg:
            try:
                await _relay_outbound(msg)
            except Exception as e:
                log.error("outbound failed: %s → %s: %s", msg.fromAddr, msg.toAddr, e)


# -- startup --


async def start(client: OMMClient2, tg: asyncio.TaskGroup) -> None:
    """Start the messaging bridge: HTTP server + outbound listener."""
    app = Starlette(
        routes=[Route("/message", partial(_handle_inbound, client), methods=["POST"])]
    )
    port = int(os.environ.get("HTTP_PORT", "8080"))
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    tg.create_task(uvicorn.Server(config).serve())

    tg.create_task(_listen_outbound(client))
