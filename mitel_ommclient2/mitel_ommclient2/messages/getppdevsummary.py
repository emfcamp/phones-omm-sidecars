#!/usr/bin/env python3

from dataclasses import dataclass
from . import Request, Response, axi_parsable


@axi_parsable
@dataclass
class GetPPDevSummaryResp(Response):
    nRecords: int | None = None
    subscribedDevs: int | None = None


@axi_parsable
@dataclass
class GetPPDevSummary(Request[GetPPDevSummaryResp]):
    pass
