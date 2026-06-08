#!/usr/bin/env python3

from dataclasses import dataclass
from . import Request, Response, axi_parsable


@axi_parsable
@dataclass
class DeletePPDevResp(Response):
    pass


@axi_parsable
@dataclass
class DeletePPDev(Request[DeletePPDevResp]):
    ppn: int = 0
