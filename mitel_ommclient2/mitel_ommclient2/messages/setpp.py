#!/usr/bin/env python3

from dataclasses import dataclass, field
from . import Request, Response, axi_parsable
from ..types import PPDevType, PPUserType


@axi_parsable
@dataclass
class SetPPResp(Response):
    pp: list[PPDevType] = field(default_factory=list)
    user: list[PPUserType] = field(default_factory=list)


@axi_parsable
@dataclass
class SetPP(Request[SetPPResp]):
    pp: list[PPDevType] = field(default_factory=list)
    user: list[PPUserType] = field(default_factory=list)
    deletedDev: bool | None = None
    deletedUser: bool | None = None
