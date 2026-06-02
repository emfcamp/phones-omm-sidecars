#!/usr/bin/env python3

from . import Request, Response, request_type, response_type


@request_type
class SetDECTAuthCode(Request):
    FIELDS = {
        "ac": str,  # Authentication Code
    }


@response_type
class SetDECTAuthCodeResp(Response):
    FIELDS = {}
