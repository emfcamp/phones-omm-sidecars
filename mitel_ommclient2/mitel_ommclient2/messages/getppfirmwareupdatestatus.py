#!/usr/bin/env python3

from dataclasses import dataclass, field
from . import Request, Response, axi_parsable
from ..types import PPFirmwareUpdateStatusType


@axi_parsable
@dataclass
class GetPPFirmwareUpdateStatusResp(Response):
    ppFwSt: list[PPFirmwareUpdateStatusType] = field(default_factory=list)


@axi_parsable
@dataclass
class GetPPFirmwareUpdateStatus(Request[GetPPFirmwareUpdateStatusResp]):
    ppn: int = 0
    maxRecords: int | None = None
