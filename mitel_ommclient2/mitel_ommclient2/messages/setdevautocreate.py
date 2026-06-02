#!/usr/bin/env python3

from . import Request, Response, request_type, response_type


@request_type
class SetDevAutoCreate(Request):
    FIELDS = {
        "enable": bool,
    }


@response_type
class SetDevAutoCreateResp(Response):
    FIELDS = {}
