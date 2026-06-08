#!/usr/bin/env python3

from dataclasses import dataclass, field
from . import Request, Response, axi_parsable
from ..types import PPUserType


@axi_parsable
@dataclass
class SetPPUserResp(Response):
    user: list[PPUserType] = field(default_factory=list)


@axi_parsable
@dataclass
class SetPPUser(Request[SetPPUserResp]):
    user: list[PPUserType] = field(default_factory=list)
