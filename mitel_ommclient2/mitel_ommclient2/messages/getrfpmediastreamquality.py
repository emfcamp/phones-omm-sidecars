#!/usr/bin/env python3

from dataclasses import dataclass, field
from . import Request, Response, axi_parsable
from ..types import MsQualityType


@axi_parsable
@dataclass
class GetRFPMediaStreamQualityResp(Response):
    msQuality: list[MsQualityType] = field(default_factory=list)


@axi_parsable
@dataclass
class GetRFPMediaStreamQuality(Request[GetRFPMediaStreamQualityResp]):
    id: int = 0
    maxRecords: int | None = None
