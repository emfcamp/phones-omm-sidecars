"""Tests for OMMClient2 methods and event subscription flow."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from mitel_ommclient2.client import OMMClient2
from mitel_ommclient2.messages import (
    EventPPDevCnf,
    EventPPTransaction,
    Subscribe,
)


@pytest.fixture
def mock_conn():
    """Create a mock connection that captures requests."""
    conn = MagicMock()
    conn.request = AsyncMock()
    conn.register_listener = MagicMock(return_value=asyncio.Queue())
    conn.unregister_listener = MagicMock()
    return conn


@pytest.fixture
def client(mock_conn):
    """Create a client with mocked connection."""
    c = OMMClient2("fake-host", "admin", "password")
    c._conn = mock_conn
    c._open_resp = MagicMock()
    return c


# -- subscribe / unsubscribe --


class TestSubscribe:
    @pytest.mark.asyncio
    async def test_subscribe_sends_correct_event_type(self, client, mock_conn):
        """Subscribe should strip 'Event' prefix from class name."""
        await client.subscribe(EventPPDevCnf, ppn=-1)
        msg = mock_conn.request.call_args[0][0]
        assert isinstance(msg, Subscribe)
        assert msg.e[0].eventType == "PPDevCnf"
        assert msg.e[0].cmd == "On"
        assert msg.e[0].ppn == -1

    @pytest.mark.asyncio
    async def test_subscribe_with_multiple_filters(self, client, mock_conn):
        await client.subscribe(EventPPTransaction, ppn=5, uid=10)
        msg = mock_conn.request.call_args[0][0]
        assert msg.e[0].ppn == 5
        assert msg.e[0].uid == 10
        assert msg.e[0].rfpId is None

    @pytest.mark.asyncio
    async def test_subscribe_no_filters(self, client, mock_conn):
        await client.subscribe(EventPPDevCnf)
        msg = mock_conn.request.call_args[0][0]
        assert msg.e[0].ppn is None
        assert msg.e[0].uid is None

    @pytest.mark.asyncio
    async def test_unsubscribe_sends_off(self, client, mock_conn):
        await client.unsubscribe(EventPPDevCnf, ppn=-1)
        msg = mock_conn.request.call_args[0][0]
        assert msg.e[0].cmd == "Off"
        assert msg.e[0].eventType == "PPDevCnf"


# -- events --


class TestEvents:
    @pytest.mark.asyncio
    async def test_events_registers_correct_listener(self, client, mock_conn):
        """events() should register listener with wire name (class name)."""
        queue = asyncio.Queue()
        queue.put_nowait(EventPPDevCnf())
        mock_conn.register_listener.return_value = queue
        async for _ in client.events(EventPPDevCnf):
            break
        mock_conn.register_listener.assert_called_once_with("EventPPDevCnf")

    @pytest.mark.asyncio
    async def test_events_unregisters_on_exit(self, client, mock_conn):
        """events() should unregister listener when the generator is closed."""
        queue = asyncio.Queue()
        queue.put_nowait(EventPPDevCnf())
        mock_conn.register_listener.return_value = queue
        gen = client.events(EventPPDevCnf)
        async for _ in gen:
            break
        await gen.aclose()
        mock_conn.unregister_listener.assert_called_once_with("EventPPDevCnf")

    @pytest.mark.asyncio
    async def test_events_yields_from_queue(self, client, mock_conn):
        """events() should yield events from the queue."""
        event = EventPPDevCnf()
        queue = asyncio.Queue()
        queue.put_nowait(event)
        mock_conn.register_listener.return_value = queue

        received = []
        async for e in client.events(EventPPDevCnf):
            received.append(e)
            break

        assert len(received) == 1
        assert received[0] is event

    @pytest.mark.asyncio
    async def test_events_multiple_events(self, client, mock_conn):
        """events() should yield multiple events."""
        queue = asyncio.Queue()
        queue.put_nowait(EventPPDevCnf())
        queue.put_nowait(EventPPDevCnf())
        queue.put_nowait(EventPPDevCnf())
        mock_conn.register_listener.return_value = queue

        count = 0
        async for _ in client.events(EventPPDevCnf):
            count += 1
            if count == 3:
                break

        assert count == 3


# -- bind / unbind --


class TestBindUnbind:
    @pytest.mark.asyncio
    async def test_bind_user_device(self, client, mock_conn):
        await client.bind_user_device(uid=42, ppn=5)
        msg = mock_conn.request.call_args[0][0]
        assert msg.user[0].uid == 42
        assert msg.user[0].ppn == 5
        assert str(msg.user[0].relType) == "Dynamic"
        assert msg.pp[0].uid == 42
        assert msg.pp[0].ppn == 5

    @pytest.mark.asyncio
    async def test_bind_user_device_custom_rel_type(self, client, mock_conn):
        await client.bind_user_device(uid=42, ppn=5, rel_type="Fixed")
        msg = mock_conn.request.call_args[0][0]
        assert str(msg.user[0].relType) == "Fixed"

    @pytest.mark.asyncio
    async def test_unbind_user_device(self, client, mock_conn):
        await client.unbind_user_device(uid=42, ppn=5)
        msg = mock_conn.request.call_args[0][0]
        assert msg.user[0].uid == 42
        assert msg.user[0].ppn == 0
        assert str(msg.user[0].relType) == "Unbound"
        assert msg.pp[0].ppn == 5
        assert msg.pp[0].uid == 0


# -- open_resp property --


class TestOpenResp:
    def test_open_resp_before_connect(self):
        c = OMMClient2("fake-host", "admin", "password")
        with pytest.raises(AssertionError, match="not connected"):
            c.open_resp

    def test_open_resp_after_connect(self, client):
        assert client.open_resp is not None
