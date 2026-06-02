#!/usr/bin/env python3

from . import Request, Response, request_type, response_type
from ..types import DECTSubscriptionModeType


@request_type
class SetDECTSubscriptionMode(Request):
    FIELDS = {
        "mode": DECTSubscriptionModeType,
        "timeout": int,  # timeout only for wildcard mode
    }


@response_type
class SetDECTSubscriptionModeResp(Response):
    FIELDS = {}
