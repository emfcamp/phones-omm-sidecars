#!/usr/bin/env python3

from dataclasses import dataclass
from . import Request, Response, axi_parsable


@axi_parsable
@dataclass
class GetPublicKeyResp(Response):
    modulus: str = ""
    exponent: str = ""


@axi_parsable
@dataclass
class GetPublicKey(Request[GetPublicKeyResp]):
    pass
