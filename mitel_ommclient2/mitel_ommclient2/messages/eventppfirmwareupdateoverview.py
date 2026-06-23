#!/usr/bin/env python3

from dataclasses import dataclass
from . import Event, axi_parsable


@axi_parsable
@dataclass
class EventPPFirmwareUpdateOverview(Event):
    state: str | None = None
    known: int | None = None
    ready: int | None = None
    pending: int | None = None
    active: int | None = None
    barred: int | None = None
    errored: int | None = None
    notReachable: int | None = None
    detached: int | None = None
    version: str | None = None
