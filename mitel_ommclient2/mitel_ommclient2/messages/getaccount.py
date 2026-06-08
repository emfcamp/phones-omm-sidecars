#!/usr/bin/env python3

from dataclasses import dataclass, field
from . import Request, Response, axi_parsable
from ..types import AccountType


@axi_parsable
@dataclass
class GetAccountResp(Response):
    account: list[AccountType] = field(default_factory=list)


@axi_parsable
@dataclass
class GetAccount(Request[GetAccountResp]):
    id: int = 0
    maxRecords: int | None = None
