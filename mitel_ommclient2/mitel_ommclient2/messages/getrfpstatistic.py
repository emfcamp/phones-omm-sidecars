#!/usr/bin/env python3

from dataclasses import dataclass, field
from . import Request, Response, axi_parsable
from ..types import RFPStatDataType


@axi_parsable
@dataclass
class GetRFPStatisticResp(Response):
    rfpStatData: list[RFPStatDataType] = field(default_factory=list)


@axi_parsable
@dataclass
class GetRFPStatistic(Request[GetRFPStatisticResp]):
    id: int = 0
    maxRecords: int | None = None
    recordSet: int | None = None
