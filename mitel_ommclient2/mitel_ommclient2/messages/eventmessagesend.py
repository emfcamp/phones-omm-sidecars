#!/usr/bin/env python3

from dataclasses import dataclass, field
from . import Event, axi_parsable
from ..types import MessageType


@axi_parsable
@dataclass
class EventMessageSend(Event):
    alwaysIndirect: bool | None = None
    msg: list[MessageType] = field(default_factory=list)
