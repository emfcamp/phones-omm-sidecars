#!/usr/bin/env python3

from dataclasses import dataclass
from . import Request, Response, axi_parsable


@axi_parsable
@dataclass
class PingResp(Response):
    timeStamp: int | None = None


@axi_parsable
@dataclass
class Ping(Request[PingResp]):
    timeStamp: int | None = None
