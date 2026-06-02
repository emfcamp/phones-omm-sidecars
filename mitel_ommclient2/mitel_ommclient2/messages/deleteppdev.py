#!/usr/bin/env python3

from . import Request, Response, request_type, response_type


@request_type
class DeletePPDev(Request):
    FIELDS = {
        "ppn": int,
    }


@response_type
class DeletePPDevResp(Response):
    pass
