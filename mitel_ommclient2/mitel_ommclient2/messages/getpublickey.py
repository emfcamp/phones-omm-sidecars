#!/usr/bin/env python3

from . import Request, Response, request_type, response_type


@request_type
class GetPublicKey(Request):
    pass


@response_type
class GetPublicKeyResp(Response):
    FIELDS = {
        "modulus": str,
        "exponent": str,
    }
