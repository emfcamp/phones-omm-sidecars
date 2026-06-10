#!/usr/bin/env python3

from dataclasses import dataclass, field
from . import Event, axi_parsable
from ..types import RFPType


@axi_parsable
@dataclass
class EventRFPCnf(Event):
    deleted: bool | None = None
    rfp: list[RFPType] = field(default_factory=list)
