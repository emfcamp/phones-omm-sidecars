#!/usr/bin/env python3

from dataclasses import dataclass
from . import Request, Response, axi_parsable


@axi_parsable
@dataclass
class DeletePPUserResp(Response):
    pass


@axi_parsable
@dataclass
class DeletePPUser(Request[DeletePPUserResp]):
    uid: int | None = None
    num: str | None = None
