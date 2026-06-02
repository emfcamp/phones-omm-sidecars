#!/usr/bin/env python3

from . import Request, Response, request_type, response_type
from ..types import PPRelTypeType


@request_type
class SetPPUserDevRelation(Request):
    FIELDS = {
        "uid": int,
        "relType": PPRelTypeType,
    }


@response_type
class SetPPUserDevRelationResp(Response):
    FIELDS = {
        "uid": int,
        "relType": PPRelTypeType,
    }
