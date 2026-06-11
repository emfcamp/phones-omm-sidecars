#!/usr/bin/env python3

from dataclasses import dataclass, field
from . import Event, axi_parsable
from ..types import IpQualityType


@axi_parsable
@dataclass
class EventRFPIpQuality(Event):
    ipQuality: list[IpQualityType] = field(default_factory=list)
