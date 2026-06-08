#!/usr/bin/env python3

from dataclasses import dataclass
from . import Request, Response, axi_parsable


@axi_parsable
@dataclass
class GetRFPSummaryResp(Response):
    nRFPs: int = 0
    nConnected: int = 0
    DECTactivatedRFPs: int | None = None
    DECTactiveRFPs: int | None = None


@axi_parsable
@dataclass
class GetRFPSummary(Request[GetRFPSummaryResp]):
    pass
