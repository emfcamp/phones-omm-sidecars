#!/usr/bin/env python3

from . import Request, Response, request_type, response_type
from ..types import PPUserType


@request_type
class GetPPUser(Request):
    FIELDS = {
        "uid": int,
        "maxRecords": int,
    }


@response_type
class GetPPUserResp(Response):
    CHILDS = {
        "user": PPUserType,
    }
