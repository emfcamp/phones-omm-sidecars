#!/usr/bin/env python3

from dataclasses import dataclass
from . import Event, axi_parsable


@axi_parsable
@dataclass
class EventPPUserSummary(Event):
    nRecords: int | None = None
    uidFirst: int | None = None
    nSipRegistration: int | None = None
    nLocatable: int | None = None
    nMsgSend: int | None = None
    usersActiveMonitored: int | None = None
    usersPassiveMonitored: int | None = None
    usersWarned: int | None = None
    usersUnavailable: int | None = None
    usersEscalated: int | None = None
