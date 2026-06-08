#!/usr/bin/env python3

from dataclasses import dataclass
from . import Request, Response, axi_parsable
from ..types import DECTSubscriptionModeType


@axi_parsable
@dataclass
class SetDECTSubscriptionModeResp(Response):
    pass


@axi_parsable
@dataclass
class SetDECTSubscriptionMode(Request[SetDECTSubscriptionModeResp]):
    mode: DECTSubscriptionModeType | None = None
    timeout: int | None = None
