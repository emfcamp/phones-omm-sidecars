#!/usr/bin/env python3

from dataclasses import dataclass, field
from . import Event, axi_parsable
from ..types import MsQualityType


@axi_parsable
@dataclass
class EventRFPMediaStreamQuality(Event):
    msQuality: list[MsQualityType] = field(default_factory=list)
