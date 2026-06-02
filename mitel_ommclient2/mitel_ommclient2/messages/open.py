#!/usr/bin/env python3

from . import Request, Response, request_type, response_type


@request_type
class Open(Request):
    FIELDS = {
        "username": None,
        "password": None,
        "UserDeviceSyncClient": None,
    }


@response_type
class OpenResp(Response):
    FIELDS = {
        "protocolVersion": None,
        "minPPSwVersion1": None,
        "minPPSwVersion2": None,
        "ommStbState": None,
        "publicKey": None,
    }
