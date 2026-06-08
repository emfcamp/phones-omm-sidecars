#!/usr/bin/env python3

from dataclasses import dataclass, field
from . import Request, Response, axi_parsable
from ..types import SubscribeCmdType


@axi_parsable
@dataclass
class SubscribeResp(Response):
    eventType: str | None = None


@axi_parsable
@dataclass
class Subscribe(Request[SubscribeResp]):
    e: list[SubscribeCmdType] = field(default_factory=list)
