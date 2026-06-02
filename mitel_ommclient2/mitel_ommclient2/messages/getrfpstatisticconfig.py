#!/usr/bin/env python3

from . import Request, Response, request_type, response_type
from ..types import RFPStatNameType


@request_type
class GetRFPStatisticConfig(Request):
    FIELDS = {}


@response_type
class GetRFPStatisticConfigResp(Response):
    CHILDS = {
        "rfpStatName": RFPStatNameType,
        "rfpStatHead": None,
    }
