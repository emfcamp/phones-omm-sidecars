#!/usr/bin/env python3

from dataclasses import dataclass
from . import Request, Response, axi_parsable
from ..types import DECTSubscriptionModeType


@axi_parsable
@dataclass
class GetDECTSubscriptionModeResp(Response):
    mode: DECTSubscriptionModeType | None = None


@axi_parsable
@dataclass
class GetDECTSubscriptionMode(Request[GetDECTSubscriptionModeResp]):
    pass
