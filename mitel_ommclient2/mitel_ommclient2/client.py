"""Async OMM client."""
from __future__ import annotations

import asyncio
import base64
import logging
from typing import Any

try:
    import rsa
except ImportError:
    rsa = None

from .connection import Connection
from . import exceptions
from . import messages
from . import types

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10.0
PING_INTERVAL = 15  # seconds


class OMMClient2:
    """Async AXI client for OMM.

    Manages connection lifecycle, authentication, and (later) transparent reconnect.
    Connection is an internal detail.

    Usage::

        async with OMMClient2("omm.local", "admin", "admin") as client:
            resp = await client.request(Ping())

    Or explicit connect/close::

        client = OMMClient2("omm.local", "admin", "admin")
        await client.connect()
        resp = await client.request(Ping())
        await client.close()
    """

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        port: int = 12622,
        use_ssl: bool = True,
        timeout: float = DEFAULT_TIMEOUT,
        ommsync: bool = False,
    ) -> None:
        self._host = host
        self._username = username
        self._password = password
        self._port = port
        self._use_ssl = use_ssl
        self._timeout = timeout
        self._ommsync = ommsync
        self._conn: Connection | None = None
        self._ping_task: asyncio.Task | None = None
        self._rsa_pubkey = None  # cached rsa.PublicKey for encrypt()
        self.open_resp = None  #: OpenResp from the initial handshake

    async def connect(self) -> None:
        """Open connection and authenticate."""
        self._conn = Connection(
            self._host, self._port, self._use_ssl, self._timeout
        )
        await self._conn.connect()
        await self._open_session()

    async def _open_session(self) -> None:
        """Send Open to authenticate with OMM."""
        m = messages.Open()
        m.username = self._username
        m.password = self._password
        if self._ommsync:
            m.UserDeviceSyncClient = "true"
        self.open_resp = await self._conn.request(m, self._timeout)
        self.open_resp.raise_on_error()
        self._ping_task = asyncio.create_task(self._ping_loop())

    async def _ping_loop(self) -> None:
        """Send periodic pings to keep the connection alive."""
        while True:
            await asyncio.sleep(PING_INTERVAL)
            try:
                await self.ping()
            except Exception:
                logger.exception("ping failed")

    async def request(self, msg, timeout=None):
        """Send a request and wait for its response.

        :param msg: Request message object
        :param timeout: Per-call timeout override, uses default if None
        """
        return await self._conn.request(msg, timeout or self._timeout)

    # -- basic requests --

    async def ping(self):
        """Is OMM still there?

        Returns True when response is received.
        """
        r = await self.request(messages.Ping())
        return r.errCode is None

    async def get_publickey(self):
        """Get OMM's RSA public key for encrypting secrets."""
        r = await self.request(messages.GetPublicKey())
        r.raise_on_error()
        return r

    async def encrypt(self, secret: str) -> str:
        """RSA-encrypt a secret for OMM (e.g. SIP password). Requires `rsa` extra."""
        if rsa is None:
            raise ImportError("rsa module is required: pip install mitel-ommclient2[crypt]")
        if self._rsa_pubkey is None:
            r = await self.get_publickey()
            self._rsa_pubkey = rsa.PublicKey(int(r.modulus, 16), int(r.exponent, 16))
        return base64.b64encode(rsa.encrypt(secret.encode(), self._rsa_pubkey)).decode()

    # -- DECT phone users --

    async def get_pp_user(self, uid: int, max_records: int = None):
        """Get one or more DECT phone users starting at uid."""
        m = messages.GetPPUser()
        m.uid = uid
        if max_records is not None:
            m.maxRecords = max_records
        return await self.request(m)

    async def set_pp_user(self, user: types.PPUserType):
        """Patch a DECT phone user. uid identifies the record, other fields are what to change."""
        m = messages.SetPPUser()
        m.childs.user = [user]
        return await self.request(m)

    async def create_pp_user(self, user: types.PPUserType = None):
        """Create a DECT phone user. OMM picks uid if not set."""
        m = messages.CreatePPUser()
        if user is not None:
            m.childs.user = [user]
        return await self.request(m)

    async def delete_pp_user(self, uid: int = None, num: str = None):
        """Delete a DECT phone user by uid or num."""
        m = messages.DeletePPUser()
        if uid is not None:
            m.uid = uid
        if num is not None:
            m.num = num
        return await self.request(m)

    # -- DECT phone devices --

    async def get_pp_dev(self, ppn: int, max_records: int = None):
        """Get one or more DECT phone devices starting at ppn."""
        m = messages.GetPPDev()
        m.ppn = ppn
        if max_records is not None:
            m.maxRecords = max_records
        return await self.request(m)

    async def delete_pp_dev(self, ppn: int):
        """Delete a DECT phone device."""
        m = messages.DeletePPDev()
        m.ppn = ppn
        return await self.request(m)

    # -- user-device binding (requires ommsync) --

    async def bind_user_device(self, uid: int, ppn: int, rel_type: str = "Dynamic"):
        """Bind a user to a device. Requires ommsync."""
        user = types.PPUserType()
        user.uid = uid
        user.ppn = ppn
        user.relType = types.PPRelTypeType(rel_type)

        pp = types.PPDevType()
        pp.ppn = ppn
        pp.uid = uid
        pp.relType = types.PPRelTypeType(rel_type)

        m = messages.SetPP()
        m.childs.user = [user]
        m.childs.pp = [pp]
        return await self.request(m)

    async def unbind_user_device(self, uid: int, ppn: int):
        """Unbind a user from a device. Requires ommsync."""
        user = types.PPUserType()
        user.uid = uid
        user.ppn = 0
        user.relType = types.PPRelTypeType("Unbound")

        pp = types.PPDevType()
        pp.ppn = ppn
        pp.uid = 0
        pp.relType = types.PPRelTypeType("Unbound")

        m = messages.SetPP()
        m.childs.user = [user]
        m.childs.pp = [pp]
        return await self.request(m)

    async def set_pp_user_dev_relation(self, uid: int, rel_type):
        """Change user-device relation type (Fixed <-> Dynamic)."""
        m = messages.SetPPUserDevRelation()
        m.uid = uid
        m.relType = rel_type
        return await self.request(m)

    # -- DECT subscription --

    async def get_dect_auth_code(self):
        """Get the DECT subscription authentication code."""
        r = await self.request(messages.GetDECTAuthCode())
        r.raise_on_error()
        return r.ac

    async def get_dect_subscription_mode(self):
        """Get current DECT subscription mode ('Configured', 'Wildcard', or 'Off')."""
        r = await self.request(messages.GetDECTSubscriptionMode())
        r.raise_on_error()
        return r.mode

    async def get_dev_auto_create(self):
        """Get whether device auto-creation on subscription is enabled."""
        r = await self.request(messages.GetDevAutoCreate())
        r.raise_on_error()
        return r.enable

    async def set_dect_auth_code(self, ac: str):
        """Set the DECT subscription authentication code."""
        m = messages.SetDECTAuthCode()
        m.ac = ac
        return await self.request(m)

    async def set_dect_subscription_mode(self, mode: str, timeout: int = None):
        """Set DECT subscription mode ('Configured', 'Wildcard', or 'Off')."""
        m = messages.SetDECTSubscriptionMode()
        m.mode = types.DECTSubscriptionModeType(mode)
        if timeout is not None:
            m.timeout = timeout
        return await self.request(m)

    async def set_dev_auto_create(self, enable: bool):
        """Set whether device auto-creation on subscription is enabled."""
        m = messages.SetDevAutoCreate()
        m.enable = enable
        return await self.request(m)

    # -- event subscriptions --

    async def subscribe(self, event_type: str, **filters):
        """Subscribe to an event type. Filters: ppn, uid, rfpId, omm, trigger, scheme.

        event_type is the spec's EventType name (e.g. "PPDevCnf", "PPState").
        Use -1 for "all" on numeric filters, "*" for wildcard on string filters.
        """
        m = messages.Subscribe()
        e = types.SubscribeCmdType()
        e.cmd = "On"
        e.eventType = event_type
        for k, v in filters.items():
            setattr(e, k, v)
        m.childs.e = [e]
        return await self.request(m)

    async def unsubscribe(self, event_type: str, **filters):
        """Unsubscribe from an event type."""
        m = messages.Subscribe()
        e = types.SubscribeCmdType()
        e.cmd = "Off"
        e.eventType = event_type
        for k, v in filters.items():
            setattr(e, k, v)
        m.childs.e = [e]
        return await self.request(m)

    async def events(self, event_type: str):
        """Async iterator over events of a given type. One listener per event_type.

        event_type is the base name (e.g. "PPDevCnf") — the same name used in
        subscribe(). Events arrive on the wire with an "Event" prefix which is
        added automatically.
        """
        wire_name = f"Event{event_type}"
        queue = self._conn.register_listener(wire_name)
        try:
            while True:
                yield await queue.get()
        finally:
            self._conn.unregister_listener(wire_name)

    # -- iterators --

    async def iter_pp_users(self, batch_size: int = 20):
        """Yield all DECT phone users, paginating automatically."""
        uid = 0
        while True:
            r = await self.get_pp_user(uid, max_records=batch_size)
            try:
                r.raise_on_error()
            except exceptions.ENoEnt:
                return
            for user in r.childs.user:
                yield user
            uid = int(r.childs.user[-1].uid) + 1

    async def iter_pp_devs(self, batch_size: int = 20):
        """Yield all DECT phone devices, paginating automatically."""
        ppn = 0
        while True:
            r = await self.get_pp_dev(ppn, max_records=batch_size)
            try:
                r.raise_on_error()
            except exceptions.ENoEnt:
                return
            for pp in r.childs.pp:
                yield pp
            ppn = int(r.childs.pp[-1].ppn) + 1

    # -- lifecycle --

    async def close(self) -> None:
        """Close connection."""
        if self._ping_task:
            self._ping_task.cancel()
            try:
                await self._ping_task
            except asyncio.CancelledError:
                pass
            self._ping_task = None
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def __aenter__(self) -> OMMClient2:
        await self.connect()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()
