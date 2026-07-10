"""AXI connection to OMM.

Manages TCP/TLS socket, null-byte framed XML message send/recv,
and seq -> Future mapping for request/response correlation.
"""

from __future__ import annotations

import asyncio
import logging
import os
import socket
import ssl

from . import messages
from .messages import Request, RespT, get_response_type

logger = logging.getLogger(__name__)

READ_TIMEOUT = 22  # seconds — 150% of ping interval (15s)


def _ssl_context() -> ssl.SSLContext:
    """Create SSL context for OMM (self-signed certs)."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


class Connection:
    """AXI connection to OMM.

    Manages a single TCP/TLS connection with:
    - Null-byte terminated XML message framing
    - seq -> Future mapping for request/response correlation
    - Background recv loop

    Usage::

        async with Connection("omm.local") as conn:
            resp = await conn.request(Ping())
    """

    def __init__(
        self,
        host: str,
        port: int = 12622,
        use_ssl: bool = True,
        timeout: float = 10.0,
    ) -> None:
        self._host = host
        self._port = port
        self._use_ssl = use_ssl
        self._timeout = timeout

        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._seq: int = 0
        self._pending: dict[int, asyncio.Future[messages.Response]] = {}
        self._event_listeners: dict[str, list[asyncio.Queue[messages.Event]]] = {}
        self._write_lock = asyncio.Lock()
        self._recv_task: asyncio.Task[None] | None = None

    async def connect(self) -> None:
        """Open TCP+TLS connection to OMM."""
        ssl_ctx = _ssl_context() if self._use_ssl else None
        self._reader, self._writer = await asyncio.wait_for(
            asyncio.open_connection(
                self._host,
                self._port,
                ssl=ssl_ctx,
                family=socket.AF_INET,
            ),
            timeout=self._timeout,
        )
        self._recv_task = asyncio.create_task(self._recv_loop())

    async def request(self, msg: Request[RespT], timeout: float | None = None) -> RespT:
        """Send request and wait for response.

        :param msg: Request message object
        :param timeout: Per-call timeout override
        """
        timeout = timeout or self._timeout
        seq = self._next_seq()
        msg.seq = seq

        future: asyncio.Future[messages.Response] = (
            asyncio.get_running_loop().create_future()
        )
        self._pending[seq] = future

        assert self._writer is not None
        async with self._write_lock:
            self._writer.write(messages.construct(msg).encode("utf-8") + b"\0")
            await self._writer.drain()

        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            assert isinstance(result, get_response_type(type(msg)))
            return result
        finally:
            self._pending.pop(seq, None)

    def _next_seq(self) -> int:
        seq = self._seq
        self._seq += 1
        return seq

    def register_listener(self, event_type: str) -> asyncio.Queue[messages.Event]:
        """Register a listener queue for an event type. Returns the queue.

        Multiple listeners per event type are supported (fanout).
        """
        queue: asyncio.Queue[messages.Event] = asyncio.Queue()
        self._event_listeners.setdefault(event_type, []).append(queue)
        return queue

    def unregister_listener(
        self, event_type: str, queue: asyncio.Queue[messages.Event]
    ) -> None:
        """Remove a specific listener queue for an event type."""
        listeners = self._event_listeners.get(event_type)
        if listeners is not None:
            try:
                listeners.remove(queue)
            except ValueError:
                pass
            if not listeners:
                del self._event_listeners[event_type]

    async def _recv_loop(self) -> None:
        """Background: read null-byte terminated messages, dispatch to pending."""
        assert self._reader is not None
        reader = self._reader
        buffer = b""
        try:
            while True:
                async with asyncio.timeout(READ_TIMEOUT):
                    data = await reader.read(4096)
                if not data:
                    logger.warning("connection closed by OMM")
                    break
                buffer += data

                while b"\0" in buffer:
                    parts = buffer.split(b"\0", 1)
                    msg_bytes = parts[0]
                    buffer = parts[1]
                    if not msg_bytes:
                        continue
                    xml = msg_bytes.decode("utf-8").strip()
                    logger.debug("incoming: %s", xml)
                    try:
                        response = messages.parse(xml)
                    except Exception:
                        logger.exception("failed to parse message: %r", msg_bytes[:200])
                        continue

                    if isinstance(response, messages.Response):
                        if response.seq is not None and response.seq in self._pending:
                            self._pending[response.seq].set_result(response)
                    else:
                        assert isinstance(response, messages.Event)
                        event_name = type(response).__name__
                        queues = self._event_listeners.get(event_name)
                        if queues:
                            for queue in queues:
                                queue.put_nowait(response)
                        else:
                            logger.warning(
                                "unhandled unsolicited message: %s", event_name
                            )

        except Exception as e:
            if isinstance(e.__cause__, asyncio.CancelledError):
                raise  # cancelled by close()
            logger.exception("recv loop error")
        finally:
            for future in self._pending.values():
                if not future.done():
                    future.cancel()
            self._pending.clear()

        # Connection died (not cancelled by close()) — hard exit after
        # giving other tasks 1s to notice via cancelled futures.
        await asyncio.sleep(1)
        os._exit(1)

    async def close(self) -> None:
        """Shut down recv loop and socket."""
        if self._recv_task:
            self._recv_task.cancel()
            try:
                await self._recv_task
            except asyncio.CancelledError:
                pass
        if self._writer:
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except Exception:
                pass

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()
