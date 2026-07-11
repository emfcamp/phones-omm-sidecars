#!/usr/bin/env python3

from dataclasses import dataclass
from . import Request, Response, axi_parsable
from ..types import PPUserCallStateType


@axi_parsable
@dataclass
class GetPPStateResp(Response):
    ppn: int = 0
    onHook: bool | None = None
    silentCharging: bool | None = None
    callState: PPUserCallStateType | None = None
    batteryLevel: int | None = None
    swVersion: str | None = None
    registered: bool | None = None
    regServerType: str | None = None
    regServerAddr: str | None = None
    regServerPort: int | None = None


@axi_parsable
@dataclass
class GetPPState(Request[GetPPStateResp]):
    ppn: int = 0
