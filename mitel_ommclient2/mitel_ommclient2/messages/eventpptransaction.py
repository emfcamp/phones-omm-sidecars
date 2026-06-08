#!/usr/bin/env python3

from dataclasses import dataclass
from . import Event, axi_parsable


@axi_parsable
@dataclass
class EventPPTransaction(Event):
    trType: str | None = None
    ppn: int | None = None
    rfpId: int | None = None
