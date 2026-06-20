#!/usr/bin/env python3

from dataclasses import dataclass, field
from . import Request, Response, axi_parsable
from ..types import MessageType


@axi_parsable
@dataclass
class SendMessageResp(Response):
    pass


@axi_parsable
@dataclass
class SendMessage(Request[SendMessageResp]):
    alwaysIndirect: bool | None = None
    msg: list[MessageType] = field(default_factory=list)
