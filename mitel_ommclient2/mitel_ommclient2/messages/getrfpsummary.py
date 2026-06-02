#!/usr/bin/env python3

from . import Request, Response, request_type, response_type


@request_type
class GetRFPSummary(Request):
    FIELDS = {}


@response_type
class GetRFPSummaryResp(Response):
    FIELDS = {
        "nRFPs": int,
        "nConnected": int,
        "DECTactivatedRFPs": int,
        "DECTactiveRFPs": int,
    }
