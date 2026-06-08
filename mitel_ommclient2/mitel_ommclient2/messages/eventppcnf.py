#!/usr/bin/env python3

from dataclasses import dataclass, field
from ._base import Event, axi_parsable
from ..types import PPDevType, PPUserType


@axi_parsable
@dataclass
class EventPPCnf(Event):
    deletedDev: bool | None = None
    deletedUser: bool | None = None
    pp: list[PPDevType] = field(default_factory=list)
    user: list[PPUserType] = field(default_factory=list)
