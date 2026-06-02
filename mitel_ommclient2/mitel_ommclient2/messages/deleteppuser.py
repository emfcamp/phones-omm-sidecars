#!/usr/bin/env python3

from . import Request, Response, request_type, response_type


@request_type
class DeletePPUser(Request):
    FIELDS = {
        "uid": int,
        "num": str,
    }


@response_type
class DeletePPUserResp(Response):
    pass
