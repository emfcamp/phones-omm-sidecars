#!/usr/bin/env python3

from dataclasses import dataclass
from . import Request, Response, axi_parsable


@axi_parsable
@dataclass
class GetPPUserSummaryResp(Response):
    nRecords: int | None = None
    nLocatable: int | None = None
    nSipRegistration: int | None = None


@axi_parsable
@dataclass
class GetPPUserSummary(Request[GetPPUserSummaryResp]):
    pass
