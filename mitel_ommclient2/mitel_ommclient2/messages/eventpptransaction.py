#!/usr/bin/env python3

from . import Event, event_type


@event_type
class EventPPTransaction(Event):
    FIELDS = {
        "trType": str,
        "ppn": int,
        "rfpId": int,
    }
