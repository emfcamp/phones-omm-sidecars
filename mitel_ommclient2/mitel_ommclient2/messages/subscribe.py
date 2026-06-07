#!/usr/bin/env python3

from . import Request, Response, request_type, response_type
from ..types import SubscribeCmdType


@request_type
class Subscribe(Request):
    CHILDS = {
        "e": SubscribeCmdType,
    }


@response_type
class SubscribeResp(Response):
    FIELDS = {
        "eventType": str,
    }
