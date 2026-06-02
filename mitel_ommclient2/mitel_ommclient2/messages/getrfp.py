#!/usr/bin/env python3

from . import Request, Response, request_type, response_type


@request_type
class GetRFP(Request):
    FIELDS = {
        "id": int,
        "maxRecords": int,
        "withState": str,
        "withDetails": str,
    }


@response_type
class GetRFPResp(Response):
    # RFP records have many optional/undocumented fields depending on OMM version;
    # kept as raw dicts to avoid strict field validation failures.
    CHILDS = {
        "rfp": None,
    }
