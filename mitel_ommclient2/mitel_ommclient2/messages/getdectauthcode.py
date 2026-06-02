#!/usr/bin/env python3

from . import Request, Response, request_type, response_type


@request_type
class GetDECTAuthCode(Request):
    FIELDS = {}


@response_type
class GetDECTAuthCodeResp(Response):
    FIELDS = {
        "ac": str,  # Authentication Code
    }
