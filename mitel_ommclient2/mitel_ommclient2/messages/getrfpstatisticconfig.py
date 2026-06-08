#!/usr/bin/env python3

from dataclasses import dataclass, field
from . import Request, Response, axi_parsable
from ..types import RFPStatHeadType, RFPStatNameType


@axi_parsable
@dataclass
class GetRFPStatisticConfigResp(Response):
    rfpStatHead: list[RFPStatHeadType] = field(default_factory=list)
    rfpStatName: list[RFPStatNameType] = field(default_factory=list)


@axi_parsable
@dataclass
class GetRFPStatisticConfig(Request[GetRFPStatisticConfigResp]):
    pass
