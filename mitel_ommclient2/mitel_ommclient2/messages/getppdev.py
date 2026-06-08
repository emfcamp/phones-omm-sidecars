#!/usr/bin/env python3

from dataclasses import dataclass, field
from . import Request, Response, axi_parsable
from ..types import PPDevType


@axi_parsable
@dataclass
class GetPPDevResp(Response):
    pp: list[PPDevType] = field(default_factory=list)


@axi_parsable
@dataclass
class GetPPDev(Request[GetPPDevResp]):
    ppn: int = 0
    maxRecords: int | None = None
