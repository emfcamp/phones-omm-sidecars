"""Tests for Connection recv loop exit behavior.

The recv loop must call os._exit(1) when the connection dies (read timeout,
OMM closes connection), but NOT when the connection is closed intentionally
via close().
"""
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from mitel_ommclient2.connection import Connection


@pytest.fixture
def conn():
    """Create a Connection with mocked reader/writer (no recv task yet)."""
    c = Connection("fake-host", use_ssl=False)
    c._reader = AsyncMock()
    c._writer = MagicMock()
    c._writer.close = MagicMock()
    c._writer.wait_closed = AsyncMock()
    return c


@pytest.mark.asyncio
async def test_os_exit_on_read_timeout(conn):
    """Read timeout means connection is dead — process must exit."""
    conn._reader.read = AsyncMock(side_effect=asyncio.TimeoutError)
    conn._recv_task = asyncio.create_task(conn._recv_loop())

    with patch("mitel_ommclient2.connection.os._exit") as mock_exit:
        await conn._recv_task
        await asyncio.sleep(1.5)
        mock_exit.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_os_exit_on_empty_read(conn):
    """Empty read means OMM closed connection — process must exit."""
    conn._reader.read = AsyncMock(return_value=b"")
    conn._recv_task = asyncio.create_task(conn._recv_loop())

    with patch("mitel_ommclient2.connection.os._exit") as mock_exit:
        await conn._recv_task
        await asyncio.sleep(1.5)
        mock_exit.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_no_os_exit_on_intentional_close(conn):
    """Intentional close() must NOT call os._exit."""
    read_block = asyncio.Event()
    async def blocking_read(_):
        await read_block.wait()
        return b""

    conn._reader.read = blocking_read
    conn._recv_task = asyncio.create_task(conn._recv_loop())

    with patch("mitel_ommclient2.connection.os._exit") as mock_exit:
        await conn.close()
        await asyncio.sleep(0.5)
        mock_exit.assert_not_called()
