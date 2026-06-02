#!/usr/bin/env python3

from . import Request, Response, request_type, response_type
from ..types import PPDevType


@request_type
class GetPPDev(Request):
    FIELDS = {
        "ppn": int,
        "maxRecords": int,
    }


@response_type
class GetPPDevResp(Response):
    CHILDS = {
        "pp": PPDevType,
    }
