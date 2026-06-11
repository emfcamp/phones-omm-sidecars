#!/usr/bin/env python3

from dataclasses import dataclass, field
from . import Request, Response, axi_parsable
from ..types import SyncQualityType


@axi_parsable
@dataclass
class GetRFPSyncQualityResp(Response):
    syncQuality: list[SyncQualityType] = field(default_factory=list)


@axi_parsable
@dataclass
class GetRFPSyncQuality(Request[GetRFPSyncQualityResp]):
    id: int = 0
    maxRecords: int | None = None
