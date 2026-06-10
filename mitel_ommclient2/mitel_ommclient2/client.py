"""Async OMM client."""

from __future__ import annotations

import asyncio
import base64
import logging
from typing import AsyncGenerator, TypeVar

import rsa

from .connection import Connection
from . import exceptions
from . import messages
from .messages import Request, RespT, OpenResp
from . import types

logger = logging.getLogger(__name__)

EventT = TypeVar("EventT", bound=messages.Event)

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
        self._ping_task: asyncio.Task[None] | None = None
        self._rsa_pubkey: rsa.PublicKey | None = None  # cached for encrypt()
        self._open_resp: OpenResp | None = None

    @property
    def open_resp(self) -> OpenResp:
        """OpenResp from the initial handshake. Fails if not connected."""
        assert self._open_resp is not None, "not connected"
        return self._open_resp

    async def connect(self) -> None:
        """Open connection and authenticate."""
        self._conn = Connection(self._host, self._port, self._use_ssl, self._timeout)
        await self._conn.connect()
        await self._open_session()

    async def _open_session(self) -> None:
        """Send Open to authenticate with OMM."""
        assert self._conn is not None
        m = messages.Open(
            username=self._username,
            password=self._password,
            UserDeviceSyncClient="true" if self._ommsync else None,
        )
        self._open_resp = await self.request(m)
        self._ping_task = asyncio.create_task(self._ping_loop())

    async def _ping_loop(self) -> None:
        """Send periodic pings to keep the connection alive."""
        while True:
            await asyncio.sleep(PING_INTERVAL)
            try:
                await self.ping()
            except Exception:
                logger.exception("ping failed")

    async def request(self, msg: Request[RespT], timeout: float | None = None) -> RespT:
        """Send a request and wait for its response. Raises on OMM error.

        :param msg: Request message object
        :param timeout: Per-call timeout override, uses default if None
        """
        assert self._conn is not None
        r = await self._conn.request(msg, timeout or self._timeout)
        r.raise_on_error()
        return r

    # -- basic requests --

    async def ping(self) -> None:
        """Is OMM still there? Raises on error."""
        await self.request(messages.Ping())

    async def get_publickey(self):
        """Get OMM's RSA public key for encrypting secrets."""
        return await self.request(messages.GetPublicKey())

    async def encrypt(self, secret: str) -> str:
        """RSA-encrypt a secret for OMM (e.g. SIP password)."""
        if self._rsa_pubkey is None:
            r = await self.get_publickey()
            self._rsa_pubkey = rsa.PublicKey(int(r.modulus, 16), int(r.exponent, 16))
        return base64.b64encode(rsa.encrypt(secret.encode(), self._rsa_pubkey)).decode()

    # -- DECT phone users --

    async def get_pp_user(self, uid: int, max_records: int | None = None):
        """Get one or more DECT phone users starting at uid."""
        m = messages.GetPPUser(uid=uid, maxRecords=max_records)
        return await self.request(m)

    async def set_pp_user(self, user: types.PPUserType):
        """Patch a DECT phone user. uid identifies the record, other fields are what to change."""
        m = messages.SetPPUser(user=[user])
        return await self.request(m)

    async def create_pp_user(self, user: types.PPUserType):
        """Create a DECT phone user. OMM picks uid if not set."""
        m = messages.CreatePPUser(user=[user])
        return await self.request(m)

    async def delete_pp_user(self, uid: int | None = None, num: str | None = None):
        """Delete a DECT phone user by uid or num."""
        m = messages.DeletePPUser(uid=uid, num=num)
        return await self.request(m)

    # -- DECT phone devices --

    async def get_pp_dev(self, ppn: int, max_records: int | None = None):
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

    async def get_pp_dev_summary(self):
        """Get DECT phone device summary."""
        return await self.request(messages.GetPPDevSummary())

    async def get_pp_user_summary(self):
        """Get DECT phone user summary."""
        return await self.request(messages.GetPPUserSummary())

    # -- user-device binding (requires ommsync) --

    async def bind_user_device(self, uid: int, ppn: int, rel_type: str = "Dynamic"):
        """Bind a user to a device. Requires ommsync."""
        rel = types.PPRelTypeType(rel_type)
        user = types.PPUserType(uid=uid, ppn=ppn, relType=rel)
        pp = types.PPDevType(ppn=ppn, uid=uid, relType=rel)
        m = messages.SetPP(user=[user], pp=[pp])
        return await self.request(m)

    async def unbind_user_device(self, uid: int, ppn: int):
        """Unbind a user from a device. Requires ommsync."""
        rel = types.PPRelTypeType("Unbound")
        user = types.PPUserType(uid=uid, ppn=0, relType=rel)
        pp = types.PPDevType(ppn=ppn, uid=0, relType=rel)
        m = messages.SetPP(user=[user], pp=[pp])
        return await self.request(m)

    async def set_pp_user_dev_relation(self, uid: int, rel_type: str):
        """Change user-device relation type (Fixed <-> Dynamic)."""
        m = messages.SetPPUserDevRelation(
            uid=uid, relType=types.PPRelTypeType(rel_type)
        )
        return await self.request(m)

    # -- DECT subscription --

    async def get_dect_auth_code(self) -> str:
        """Get the DECT subscription authentication code."""
        r = await self.request(messages.GetDECTAuthCode())
        return r.ac

    async def get_dect_subscription_mode(self) -> types.DECTSubscriptionModeType | None:
        """Get current DECT subscription mode ('Configured', 'Wildcard', or 'Off')."""
        r = await self.request(messages.GetDECTSubscriptionMode())
        return r.mode

    async def get_dev_auto_create(self) -> bool:
        """Get whether device auto-creation on subscription is enabled."""
        r = await self.request(messages.GetDevAutoCreate())
        return r.enable

    async def set_dect_auth_code(self, ac: str):
        """Set the DECT subscription authentication code."""
        m = messages.SetDECTAuthCode(ac=ac)
        return await self.request(m)

    async def set_dect_subscription_mode(self, mode: str, timeout: int | None = None):
        """Set DECT subscription mode ('Configured', 'Wildcard', or 'Off')."""
        m = messages.SetDECTSubscriptionMode(
            mode=types.DECTSubscriptionModeType(mode),
            timeout=timeout,
        )
        return await self.request(m)

    async def set_dev_auto_create(self, enable: bool):
        """Set whether device auto-creation on subscription is enabled."""
        m = messages.SetDevAutoCreate(enable=enable)
        return await self.request(m)

    # -- event subscriptions --

    async def subscribe(
        self,
        event_cls: type[messages.Event],
        ppn: int | None = None,
        uid: int | None = None,
        rfpId: int | None = None,
        omm: int | None = None,
        trigger: str | None = None,
        scheme: str | None = None,
    ) -> messages.SubscribeResp:
        """Subscribe to an event type.

        Use -1 for "all" on numeric filters, "*" for wildcard on string filters.
        """
        cmd = types.SubscribeCmdType(
            cmd="On",
            eventType=event_cls.__name__.removeprefix("Event"),
            ppn=ppn,
            uid=uid,
            rfpId=rfpId,
            omm=omm,
            trigger=trigger,
            scheme=scheme,
        )
        return await self.request(messages.Subscribe(e=[cmd]))

    async def unsubscribe(
        self,
        event_cls: type[messages.Event],
        ppn: int | None = None,
        uid: int | None = None,
        rfpId: int | None = None,
        omm: int | None = None,
        trigger: str | None = None,
        scheme: str | None = None,
    ) -> messages.SubscribeResp:
        """Unsubscribe from an event type."""
        cmd = types.SubscribeCmdType(
            cmd="Off",
            eventType=event_cls.__name__.removeprefix("Event"),
            ppn=ppn,
            uid=uid,
            rfpId=rfpId,
            omm=omm,
            trigger=trigger,
            scheme=scheme,
        )
        return await self.request(messages.Subscribe(e=[cmd]))

    async def events(self, event_cls: type[EventT]) -> AsyncGenerator[EventT, None]:
        """Async iterator over events of a given type. One listener per event_type.

        Events arrive on the wire with an "Event" prefix which is added automatically.
        """
        assert self._conn is not None
        event_name = event_cls.__name__
        queue = self._conn.register_listener(event_name)
        try:
            while True:
                event = await queue.get()
                assert isinstance(event, event_cls)
                yield event
        finally:
            self._conn.unregister_listener(event_name)

    # -- iterators --

    async def pp_users(
        self, batch_size: int = 20
    ) -> AsyncGenerator[types.PPUserType, None]:
        """Yield all DECT phone users, paginating automatically."""
        uid = 0
        while True:
            try:
                r = await self.get_pp_user(uid, max_records=batch_size)
            except exceptions.ENoEnt:
                return
            for user in r.user:
                yield user
            uid = int(r.user[-1].uid) + 1

    async def pp_devs(
        self, batch_size: int = 20
    ) -> AsyncGenerator[types.PPDevType, None]:
        """Yield all DECT phone devices, paginating automatically."""
        ppn = 0
        while True:
            try:
                r = await self.get_pp_dev(ppn, max_records=batch_size)
            except exceptions.ENoEnt:
                return
            for pp in r.pp:
                yield pp
            ppn = int(r.pp[-1].ppn) + 1

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

    async def __aexit__(self, *_) -> None:
        await self.close()
