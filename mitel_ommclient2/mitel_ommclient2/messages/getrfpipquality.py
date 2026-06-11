#!/usr/bin/env python3

from dataclasses import dataclass, field
from . import Request, Response, axi_parsable
from ..types import IpQualityType


@axi_parsable
@dataclass
class GetRFPIpQualityResp(Response):
    ipQuality: list[IpQualityType] = field(default_factory=list)


@axi_parsable
@dataclass
class GetRFPIpQuality(Request[GetRFPIpQualityResp]):
    id: int = 0
    maxRecords: int | None = None
