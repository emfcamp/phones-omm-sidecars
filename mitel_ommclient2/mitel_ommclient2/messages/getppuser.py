#!/usr/bin/env python3

from dataclasses import dataclass, field
from . import Request, Response, axi_parsable
from ..types import PPUserType


@axi_parsable
@dataclass
class GetPPUserResp(Response):
    user: list[PPUserType] = field(default_factory=list)


@axi_parsable
@dataclass
class GetPPUser(Request[GetPPUserResp]):
    uid: int = 0
    maxRecords: int | None = None
