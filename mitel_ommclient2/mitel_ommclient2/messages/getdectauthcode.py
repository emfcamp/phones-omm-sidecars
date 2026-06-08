#!/usr/bin/env python3

from dataclasses import dataclass
from . import Request, Response, axi_parsable


@axi_parsable
@dataclass
class GetDECTAuthCodeResp(Response):
    ac: str = ""


@axi_parsable
@dataclass
class GetDECTAuthCode(Request[GetDECTAuthCodeResp]):
    pass
