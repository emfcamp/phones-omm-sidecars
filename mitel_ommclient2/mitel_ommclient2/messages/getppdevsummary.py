#!/usr/bin/env python3

from . import Request, Response, request_type, response_type


@request_type
class GetPPDevSummary(Request):
    FIELDS = {}


@response_type
class GetPPDevSummaryResp(Response):
    FIELDS = {
        "nRecords": int,
        "subscribedDevs": int,
    }
