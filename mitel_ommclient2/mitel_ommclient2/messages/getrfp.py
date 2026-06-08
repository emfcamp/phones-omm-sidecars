#!/usr/bin/env python3

from dataclasses import dataclass, field
from . import Request, Response, axi_parsable
from ..types import RFPType


@axi_parsable
@dataclass
class GetRFPResp(Response):
    rfp: list[RFPType] = field(default_factory=list)


@axi_parsable
@dataclass
class GetRFP(Request[GetRFPResp]):
    id: int = 0
    maxRecords: int | None = None
    withState: str | None = None
    withDetails: str | None = None
