#!/usr/bin/env python3

from . import Request, Response, request_type, response_type
from ..types import DECTSubscriptionModeType


@request_type
class GetDECTSubscriptionMode(Request):
    FIELDS = {}


@response_type
class GetDECTSubscriptionModeResp(Response):
    FIELDS = {
        "mode": DECTSubscriptionModeType,
    }
