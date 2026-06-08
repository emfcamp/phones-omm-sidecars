#!/usr/bin/env python3

from dataclasses import dataclass, field
from . import Event, axi_parsable
from ..types import PPDevType


@axi_parsable
@dataclass
class EventPPDevCnf(Event):
    deleted: bool | None = None
    pp: list[PPDevType] = field(default_factory=list)
