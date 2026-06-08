#!/usr/bin/env python3

from dataclasses import dataclass
from . import Request, Response, axi_parsable


@axi_parsable
@dataclass
class OpenResp(Response):
    # mandatory (yes)
    protocolVersion: int = 0
    minPPSwVersion1: str = ""
    minPPSwVersion2: str = ""
    minPPSwVersion3: str = ""
    minPPSwVersion4: str = ""
    ommStbState: str = ""
    # optional
    ommVersion: str | None = None
    ommAxiSpecVersion: str | None = None
    axiClients: int | None = None
    cloudId: str | None = None
    sari: str | None = None
    ommStbAddr: str | None = None
    ommStream: str | None = None
    ommPlatform: str | None = None
    uptime: int | None = None
    EULAConfirm: bool | None = None
    haveMOMAppl: bool | None = None
    haveDECTPpSettings: bool | None = None
    haveEnrolmentPP: bool | None = None
    haveLocating: bool | None = None
    haveOmmLogForward: bool | None = None
    haveOMP: bool | None = None
    havePagingAreas: bool | None = None
    haveRFPOMM: bool | None = None
    haveUMO: bool | None = None
    GDPREnabled: bool | None = None
    GDPRComplianceText: str | None = None


@axi_parsable
@dataclass
class Open(Request[OpenResp]):
    username: str = ""
    password: str = ""
    UserDeviceSyncClient: str | None = None
