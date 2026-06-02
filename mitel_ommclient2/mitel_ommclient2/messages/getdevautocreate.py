#!/usr/bin/env python3

from . import Request, Response, request_type, response_type


@request_type
class GetDevAutoCreate(Request):
    FIELDS = {}


@response_type
class GetDevAutoCreateResp(Response):
    FIELDS = {
        "enable": bool,
    }
