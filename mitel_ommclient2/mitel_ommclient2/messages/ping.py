#!/usr/bin/env python3

from . import Request, Response, request_type, response_type


@request_type
class Ping(Request):
    FIELDS = {
        "timeStamp": int,
    }


@response_type
class PingResp(Response):
    FIELDS = {
        "timeStamp": int,
    }
