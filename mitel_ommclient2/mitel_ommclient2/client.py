"""Async OMM client."""
from __future__ import annotations

import logging
from typing import Any

from .connection import Connection
from . import exceptions
from . import messages
from . import types

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10.0


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
        return int(r.modulus, 16), int(r.exponent, 16)

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
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def __aenter__(self) -> OMMClient2:
        await self.connect()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()
