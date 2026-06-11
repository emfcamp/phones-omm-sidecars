#!/usr/bin/env python3

from dataclasses import dataclass, field
from . import Event, axi_parsable
from ..types import SyncQualityType


@axi_parsable
@dataclass
class EventRFPSyncQuality(Event):
    syncQuality: list[SyncQualityType] = field(default_factory=list)
