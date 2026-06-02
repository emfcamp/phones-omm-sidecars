#!/usr/bin/env python3

from . import Request, Response, request_type, response_type
from ..types import PPUserType


@request_type
class SetPPUser(Request):
    CHILDS = {
        "user": PPUserType,
    }


@response_type
class SetPPUserResp(Response):
    CHILDS = {
        "user": PPUserType,
    }
