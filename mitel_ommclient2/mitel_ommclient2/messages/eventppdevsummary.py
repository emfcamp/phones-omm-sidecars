#!/usr/bin/env python3

from dataclasses import dataclass
from . import Event, axi_parsable


@axi_parsable
@dataclass
class EventPPDevSummary(Event):
    nRecords: int | None = None
    ppnFirst: int | None = None
    subscribedDevs: int | None = None
