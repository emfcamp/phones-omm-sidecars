#!/usr/bin/env python3

from dataclasses import dataclass
from . import Request, Response, axi_parsable


@axi_parsable
@dataclass
class SetDECTAuthCodeResp(Response):
    pass


@axi_parsable
@dataclass
class SetDECTAuthCode(Request[SetDECTAuthCodeResp]):
    ac: str = ""
