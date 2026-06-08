#!/usr/bin/env python3

from dataclasses import dataclass
from . import Request, Response, axi_parsable
from ..types import PPRelTypeType


@axi_parsable
@dataclass
class SetPPUserDevRelationResp(Response):
    uid: int | None = None
    relType: PPRelTypeType | None = None


@axi_parsable
@dataclass
class SetPPUserDevRelation(Request[SetPPUserDevRelationResp]):
    uid: int = 0
    relType: PPRelTypeType | None = None
