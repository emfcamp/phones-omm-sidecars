#!/usr/bin/env python3

from . import Request, Response, request_type, response_type


@request_type
class Open(Request):
    FIELDS = {
        "username": None,
        "password": None,
        "UserDeviceSyncClient": None,
    }


# OpenResp fields per OM AXI spec section 4.1.1 (see spec/04.01-basic-requests.txt).
# The set here is the full element table from the 9.1 spec; only the first five
# were in the upstream 6.1 fork. Marked "yes" in the spec means the OMM/MOM always
# sends the field on a successful open; the rest are optional but still part of
# the schema and may be populated depending on license/standby state.
@response_type
class OpenResp(Response):
    FIELDS = {
        # yes, integer
        "protocolVersion": None,
        # no, string — full OMM/MOM version, e.g. "3.0 RC1 Build 1"
        "ommVersion": None,
        # no, string — OM AXI spec version the server implements, e.g. "9.1"
        "ommAxiSpecVersion": None,
        # no, integer — currently connected AXI clients
        "axiClients": None,
        # yes, string — minimal DECT phone SW versions
        "minPPSwVersion1": None,
        "minPPSwVersion2": None,
        "minPPSwVersion3": None,
        "minPPSwVersion4": None,
        # no, string — cloud id, format "001F10187345"
        "cloudId": None,
        # no, string — used SARI, format "1F10187326"
        "sari": None,
        # no, sequence of accountStateType
        "accountState": None,
        # no, sequence of PermissionType
        "permission": None,
        # yes, enumeration — OMM standby state
        "ommStbState": None,
        # no, string — peer OMM IP when standby is active
        "ommStbAddr": None,
        # no, string — e.g. "ffsip", "scsip"; informational only
        "ommStream": None,
        # no, string — e.g. "linux-pc", "rfp"; informational only
        "ommPlatform": None,
        # no, integer — seconds since last OMM/MOM start
        "uptime": None,
        # no, boolean — "1"/"true" once EULA has been confirmed
        "EULAConfirm": None,
        # yes, PublicKeyType
        "publicKey": None,
    }
