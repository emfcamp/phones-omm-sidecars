#!/usr/bin/env python3

"""Dummy event for subscription topic RFPMsQuality.

The OMM subscription topic is "RFPMsQuality" but the wire event name is
"EventRFPMediaStreamQuality". This class exists only for subscribe() to
derive the correct topic name. Wire events are parsed as
EventRFPMediaStreamQuality.
"""

from dataclasses import dataclass
from . import Event, axi_parsable


@axi_parsable
@dataclass
class EventRFPMsQuality(Event):
    pass
