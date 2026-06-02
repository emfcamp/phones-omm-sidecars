#!/usr/bin/env python3

from . import Request, Response, request_type, response_type


@request_type
class GetPPUserSummary(Request):
    FIELDS = {}


@response_type
class GetPPUserSummaryResp(Response):
    FIELDS = {
        "nRecords": int,
        "nLocatable": int,
        "nSipRegistration": int,
    }
