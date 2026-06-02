#!/usr/bin/env python3

import base64
try:
    # This is is only dependency not from the modules inlcuded in python by default, so we make it optional
    import rsa
except ImportError:
    rsa = None

from .connection import Connection
from . import exceptions
from . import messages
from . import types

class OMMClient2:
    """
        High level wrapper for the OM Application XML Interface

        This class tries to provide functions for often used methods without the
        need of using the underlying messaging protocol

        :param host: Hostname or IP address of the OMM
        :param username: Username
        :param password: Password
        :param port: Port where to access the API, if None, use default value
        :param use_ssl: Whenever SSL should be used for the connetion, if None, use default value
        :param timeout: The timeout used for the connection, if None, use default value
        :param ommsync: If True login as OMM-Sync client. Some operations in OMM-Sync mode might lead to destroy DECT paring.

        Usage::

            >>> c = OMMClient2("omm.local", "admin", "admin")
            >>> c.ping()

        Use request to send custom messages::

            >>> r = s.connection.request(mitel_ommclient2.messages.Ping())
    """

    def __init__(self, host, username, password, port=None, use_ssl=None, timeout=None, ommsync=False):
        self._host = host
        self._username = username
        self._password = password
        self._port = port
        self._ommsync = ommsync

        # prepare connect arguments
        kwargs = {}
        for key in ["port", "use_ssl", "timeout"]:
            if locals()[key] is not None:
                kwargs[key] = locals()[key]

        # Connect
        self.connection = Connection(self._host, **kwargs)
        self.connection.connect()

        # Login
        m = messages.Open()
        m.username = self._username
        m.password = self._password
        if self._ommsync:
            m.UserDeviceSyncClient = "true"
        r = self.connection.request(m)
        r.raise_on_error()

    def attach_user_device(self, uid, ppn):
        """
            Attach user to device

            :param uid: User id
            :param ppn: Device id

            Requires ommsync=True
        """
        t_u = types.PPUserType()
        t_u.uid = uid
        t_u.ppn = ppn
        t_u.relType = types.PPRelTypeType("Dynamic")
        t_d = types.PPDevType()
        t_d.ppn = ppn
        t_d.uid = uid
        t_d.relType = types.PPRelTypeType("Dynamic")
        m = messages.SetPP()
        m.childs.user = [t_u]
        m.childs.pp = [t_d]
        r = self.connection.request(m)
        r.raise_on_error()
        if r.childs.user is None:
            return None
        return r.childs.user[0], r.childs.pp[0]

    def create_user(self, num):
        """
            Create PP user

            :param num: User number
        """
        t = types.PPUserType()
        t.num = num
        m = messages.CreatePPUser()
        m.childs.user = [t]
        r = self.connection.request(m)
        r.raise_on_error()
        if r.childs.user is None:
            return None
        return r.childs.user[0]

    def delete_device(self, ppn):
        """
            Delete PP device

            :param ppn: Device id
        """
        m = messages.DeletePPDev()
        m.ppn = ppn
        r = self.connection.request(m)
        r.raise_on_error()

    def delete_user(self, uid, num=None):
        """
            Delete PP user

            :param uid: User id of DECT phone
            :param num: (optional) Phone number or SIP user id
        """
        m = messages.DeletePPUser()
        m.uid = uid
        if num is not None:
            m.num = num
        r = self.connection.request(m)
        r.raise_on_error()

    def detach_user_device(self, uid, ppn):
        """
            Detach user from device

            :param uid: User id
            :param ppn: Device id

            Requires ommsync=True
        """
        t_u = types.PPUserType()
        t_u.uid = uid
        t_u.ppn = 0
        t_u.relType = types.PPRelTypeType("Unbound")
        t_d = types.PPDevType()
        t_d.ppn = ppn
        t_d.uid = 0
        t_d.relType = types.PPRelTypeType("Unbound")
        m = messages.SetPP()
        m.childs.user = [t_u]
        m.childs.pp = [t_d]
        r = self.connection.request(m)
        r.raise_on_error()
        if r.childs.user is None:
            return None
        return r.childs.user[0], r.childs.pp[0]

    def detach_user_device_by_user(self, uid):
        """
            Detach user from device

            This just requires the user id

            :param uid: User id

            Requires ommsync=True
        """
        u = self.get_user(uid)
        return self.detach_user_device(uid, u.ppn)

    def detach_user_device_by_device(self, ppn):
        """
            Detach user from device

            This just requires the device id

            :param ppn: Device id

            Requires ommsync=True
        """
        d = self.get_device(ppn)
        return self.detach_user_device(d.uid, ppn)

    def encrypt(self, secret):
        """
            Encrypt secret for OMM

            Required rsa module to be installed

            :param secret: String to encrypt
        """

        if rsa is None:
            raise Exception("rsa module is required for excryption")
        publickey = self.get_publickey()
        pubkey = rsa.PublicKey(*publickey)
        byte_secret = secret.encode('utf8')
        byte_encrypt = rsa.encrypt(byte_secret, pubkey)
        encrypt = base64.b64encode(byte_encrypt).decode("utf8")
        return encrypt

    def find_devices(self, filter):
        """
            Get all devices matching a filter

            :param filter: function taking one parameter which is a device, returns True to keep, False to discard

            Usage::

                >>> c.find_devices(lambda d: d.relType == mitel_ommclient2.types.PPRelTypeType("Unbound"))
        """

        for d in self.get_devices():
            if filter(d):
                yield d

    def find_users(self, filter):
        """
            Get all users matching a filter

            :param filter: function taking one parameter which is a user, returns True to keep, False to discard

            Usage::

                >>> c.find_users(lambda u: u.num.startswith("9998"))
        """

        for u in self.get_users():
            if filter(u):
                yield u

    def get_dect_auth_code(self):
        """
            Get DECT authentication code

            :returns: authentication code used for subscription
        """
        m = messages.GetDECTAuthCode()
        r = self.connection.request(m)
        r.raise_on_error()
        return r.ac

    def get_dect_subscription_mode(self):
        """
            Get dect subscription mode

            :returns: "Wildcard", "Configured" or "Off"
        """
        m = messages.GetDECTSubscriptionMode()
        r = self.connection.request(m)
        r.raise_on_error()
        return r.mode.value

    def get_device_auto_create(self):
        """
            get device auto create

            :returns: A bool indicating if the feature is enabled
        """
        m = messages.GetDevAutoCreate()
        r = self.connection.request(m)
        r.raise_on_error()
        return r.enable

    def get_account(self, id):
        """
            Get account

            :param id: User id
        """

        m = messages.GetAccount()
        m.id = id
        r = self.connection.request(m)
        r.raise_on_error()
        if r.childs.account is None:
            return None
        return r.childs.account[0]

    def get_device(self, ppn):
        """
            Get PP device

            :param ppn: Device id
        """

        m = messages.GetPPDev()
        m.ppn = ppn
        r = self.connection.request(m)
        r.raise_on_error()
        if r.childs.pp is None:
            return None
        return r.childs.pp[0]

    def get_devices(self):
        """
            Get all PP devices
        """
        next_ppn = 0
        while True:
            m = messages.GetPPDev()
            m.ppn = next_ppn
            m.maxRecords = 20
            r = self.connection.request(m)
            try:
                r.raise_on_error()
            except exceptions.ENoEnt:
                # No more devices to fetch
                break

            # Output all found devices
            for pp in r.childs.pp:
                yield pp

            # Determine next possible ppn
            next_ppn = int(pp.ppn) + 1

    def get_publickey(self):
        """
            Get public key for encrypted values
        """
        m = messages.GetPublicKey()
        r = self.connection.request(m)
        r.raise_on_error()
        return int(r.modulus, 16), int(r.exponent, 16)

    def get_user(self, uid):
        """
            Get PP user

            :param uid: User id
        """
        m = messages.GetPPUser()
        m.uid = uid
        r = self.connection.request(m)
        r.raise_on_error()
        if r.childs.user is None:
            return None
        return r.childs.user[0]

    def get_users(self):
        """
            Get all PP users
        """
        next_uid = 0
        while True:
            m = messages.GetPPUser()
            m.uid = next_uid
            m.maxRecords = 20
            r = self.connection.request(m)
            try:
                r.raise_on_error()
            except exceptions.ENoEnt:
                # No more devices to fetch
                break

            # Output all found devices
            for user in r.childs.user:
                yield user

            # Determine next possible ppn
            next_uid = int(user.uid) + 1

    def ping(self):
        """
            Is OMM still there?

            Returns `True` when response is received.
        """

        r = self.connection.request(messages.Ping())
        if r.errCode is None:
            return True
        return False

    def set_dect_auth_code(self, authentication_code):
        """
            Set DECT authentication code

            :param authentication_code: authentication code used for subscription
        """
        m = messages.SetDECTAuthCode()
        m.ac = authentication_code
        r = self.connection.request(m)
        r.raise_on_error()

    def set_dect_subscription_mode(self, mode, timeout=3):
        """
            Set DECT subscription mode

            :param mode: "Wildcard", "Configured" or "Off"
            :param timeout: minutes as integer, only for wildcard mode
        """
        m = messages.SetDECTSubscriptionMode()
        m.mode = types.DECTSubscriptionModeType(mode)
        m.timeout = timeout
        r = self.connection.request(m)
        r.raise_on_error()

    def set_device_auto_create(self, enable):
        """
            Set device auto create

            :param enable: Whenever to enable this feature
        """
        m = messages.SetDevAutoCreate()
        m.enable = enable
        r = self.connection.request(m)
        r.raise_on_error()

    def set_user_name(self, uid, name):
        """
            Set PP user name

            :param uid: User id
            :param name: User name
        """
        t = types.PPUserType()
        t.uid = uid
        t.name = name
        m = messages.SetPPUser()
        m.childs.user = [t]
        r = self.connection.request(m)
        r.raise_on_error()
        if r.childs.user is None:
            return None
        return r.childs.user[0]

    def set_user_num(self, uid, num):
        """
            Set PP user number

            :param uid: User id
            :param num: User number
        """
        t = types.PPUserType()
        t.uid = uid
        t.num = num
        m = messages.SetPPUser()
        m.childs.user = [t]
        r = self.connection.request(m)
        r.raise_on_error()
        if r.childs.user is None:
            return None
        return r.childs.user[0]

    def set_user_relation_dynamic(self, uid):
        """
            Set PP user to PP device relation to dynamic type

            :param uid: User id
        """
        m = messages.SetPPUserDevRelation()
        m.uid = uid
        m.relType = types.PPRelTypeType("Dynamic")
        r = self.connection.request(m)
        r.raise_on_error()

    def set_user_relation_fixed(self, uid):
        """
            Set PP user to PP device relation to fixed type

            :param uid: User id
        """
        m = messages.SetPPUserDevRelation()
        m.uid = uid
        m.relType = types.PPRelTypeType("Fixed")
        r = self.connection.request(m)
        r.raise_on_error()

    def set_user_sipauth(self, uid, sipAuthId, sipPw):
        """
            Set PP user sip credentials

            :param uid: User id
            :param sipAuthId: SIP user name
            :param sipPw: Plain text password
        """
        t = types.PPUserType()
        t.uid = uid
        t.sipAuthId = sipAuthId
        t.sipPw = self.encrypt(sipPw)
        m = messages.SetPPUser()
        m.childs.user = [t]
        r = self.connection.request(m)
        r.raise_on_error()
        if r.childs.user is None:
            return None
        return r.childs.user[0]
