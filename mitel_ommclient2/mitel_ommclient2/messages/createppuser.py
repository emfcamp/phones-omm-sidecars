#!/usr/bin/env python3

from . import Request, Response, request_type, response_type
from ..types import PPUserType


@request_type
class CreatePPUser(Request):
    CHILDS = {
        "user": PPUserType,
    }


@response_type
class CreatePPUserResp(Response):
    CHILDS = {
        "user": PPUserType,
    }
