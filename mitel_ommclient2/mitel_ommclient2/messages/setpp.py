#!/usr/bin/env python3

from . import Request, Response, request_type, response_type
from ..types import PPDevType, PPUserType


@request_type
class SetPP(Request):
    CHILDS = {
        "pp": PPDevType,
        "user": PPUserType,
    }


@response_type
class SetPPResp(Response):
    CHILDS = {
        "pp": PPDevType,
        "user": PPUserType,
    }
