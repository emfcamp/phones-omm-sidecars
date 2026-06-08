#!/usr/bin/env python3

from dataclasses import dataclass
from . import Request, Response, axi_parsable


@axi_parsable
@dataclass
class GetDevAutoCreateResp(Response):
    enable: bool = False


@axi_parsable
@dataclass
class GetDevAutoCreate(Request[GetDevAutoCreateResp]):
    pass
