#!/usr/bin/env python3

from . import Event, event_type
from ..types import PPDevType


@event_type
class EventPPDevCnf(Event):
    FIELDS = {
        "deleted": bool,
    }
    CHILDS = {
        "pp": PPDevType,
    }
