#!/usr/bin/env python3

from dataclasses import dataclass
from . import Request, Response, axi_parsable


@axi_parsable
@dataclass
class SetDevAutoCreateResp(Response):
    pass


@axi_parsable
@dataclass
class SetDevAutoCreate(Request[SetDevAutoCreateResp]):
    enable: bool = False
