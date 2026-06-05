"""AXI connection to OMM.

Manages TCP/TLS socket, null-byte framed XML message send/recv,
and seq -> Future mapping for request/response correlation.
"""
from __future__ import annotations

import asyncio
import logging
import socket
import ssl

from . import messages

logger = logging.getLogger(__name__)


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
        self._pending: dict[int, asyncio.Future] = {}
        self._write_lock = asyncio.Lock()
        self._recv_task: asyncio.Task | None = None

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

    async def request(self, msg, timeout=None):
        """Send request and wait for response.

        :param msg: Request message object
        :param timeout: Per-call timeout override
        """
        timeout = timeout or self._timeout
        seq = self._next_seq()
        msg.seq = seq

        future = asyncio.get_running_loop().create_future()
        self._pending[seq] = future

        async with self._write_lock:
            self._writer.write(messages.construct(msg).encode("utf-8") + b"\0")
            await self._writer.drain()

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        finally:
            self._pending.pop(seq, None)

    def _next_seq(self) -> int:
        seq = self._seq
        self._seq += 1
        return seq

    async def _recv_loop(self) -> None:
        """Background: read null-byte terminated messages, dispatch to pending."""
        buffer = b""
        try:
            while True:
                data = await self._reader.read(4096)
                if not data:
                    logger.warning("connection closed by OMM")
                    break
                buffer += data

                while b"\0" in buffer:
                    msg_bytes, buffer = buffer.split(b"\0", 1)
                    if not msg_bytes:
                        continue
                    try:
                        response = messages.parse(msg_bytes.decode("utf-8"))
                    except Exception:
                        logger.exception("failed to parse message: %r", msg_bytes[:200])
                        continue

                    seq = getattr(response, "seq", None)
                    if seq is not None and seq in self._pending:
                        self._pending[seq].set_result(response)
                    else:
                        logger.debug("unsolicited message (seq=%s): %s", seq, response.name)

        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("recv loop error")
        finally:
            for future in self._pending.values():
                if not future.done():
                    future.cancel()
            self._pending.clear()

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

    async def __aexit__(self, *exc):
        await self.close()
