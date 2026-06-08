#!/usr/bin/env python3

from dataclasses import dataclass


# -- enums --


class EnumType:
    VALUES: list[str] | None = []

    def __init__(self, s: str):
        if self.VALUES is not None:
            if s in self.VALUES:
                self.value = s
            else:
                raise ValueError()
        else:
            self.value = s

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.value!r})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and self.value == other.value


class CallForwardStateType(EnumType):
    VALUES = ["Off", "Busy", "NoAnswer", "BusyNoAnswer", "All"]


class DECTSubscriptionModeType(EnumType):
    VALUES = ["Wildcard", "Configured", "Off"]


class DECTSubscriptionStateType(EnumType):
    VALUES = None


class LanguageType(EnumType):
    VALUES = None


class MonitoringStateType(EnumType):
    VALUES = None


class PPRelTypeType(EnumType):
    VALUES = ["Fixed", "Dynamic", "Unbound"]


# -- child types (dataclasses) --


@dataclass
class SubscribeCmdType:
    cmd: str = ""
    eventType: str = ""
    ppn: int | None = None
    uid: int | None = None
    rfpId: int | None = None
    omm: int | None = None
    trigger: str | None = None
    scheme: str | None = None


@dataclass
class AccountType:
    id: int = 0
    username: str = ""
    password: str = ""
    oldPassword: str = ""
    active: bool = False
    expire: int | None = None
    state: str = ""


@dataclass
class PPDevType:
    ppn: int = 0
    timeStamp: int | None = None
    relType: PPRelTypeType | None = None
    uid: int | None = None
    ipei: str | None = None
    ac: str | None = None
    s: DECTSubscriptionStateType | None = None
    uak: str | None = None
    encrypt: bool | None = None
    capMessaging: bool | None = None
    capMessagingForInternalUse: bool | None = None
    capEnhLocating: bool | None = None
    capBluetooth: bool | None = None
    ethAddr: str | None = None
    hwType: str | None = None
    ppProfileCapability: bool | None = None
    ppDefaultProfileLoaded: bool | None = None
    subscribeToPARIOnly: bool | None = None
    ommId: str | None = None
    ommIdAck: str | None = None
    timeStampAdmin: int | None = None
    timeStampRelation: int | None = None
    timeStampRoaming: int | None = None
    timeStampSubscription: int | None = None
    autoCreate: bool | None = None
    modicType: str | None = None
    locationData: str | None = None
    dectIeFixedId: str | None = None
    subscriptionId: str | None = None
    ppnSec: int | None = None


@dataclass
class RFPStatNameType:
    elemId: int = 0
    group: str = ""
    name: str = ""


@dataclass
class RFPType:
    """Stub — RFPType has many fields depending on OMM version."""

    id: int = 0
    ethAddr: str = ""
    dectOn: bool = False
    name: str = ""


@dataclass
class RFPStatHeadType:
    numElemPerRec: int = 0
    recordSets: int = 0
    resolution: str = ""


@dataclass
class RFPStatDataType:
    id: int = 0
    counter: str = ""


@dataclass
class PPUserType:
    uid: int = 0
    timeStamp: int | None = None
    relType: PPRelTypeType | None = None
    ppn: int | None = None
    name: str | None = None
    num: str | None = None
    hierarchy1: str | None = None
    hierarchy2: str | None = None
    addId: str | None = None
    pin: str | None = None
    sipAuthId: str | None = None
    sipPw: str | None = None
    sosNum: str | None = None
    voiceboxNum: str | None = None
    manDownNum: str | None = None
    forwardState: CallForwardStateType | None = None
    forwardTime: int | None = None
    forwardDest: str | None = None
    langPP: LanguageType | None = None
    holdRingBackTime: int | None = None
    autoAnswer: str | None = None
    microphoneMute: str | None = None
    warningTone: str | None = None
    allowBargeIn: str | None = None
    callWaitingDisabled: bool | None = None
    external: bool | None = None
    trackingActive: bool | None = None
    locatable: bool | None = None
    BTlocatable: bool | None = None
    BTsensitivity: str | None = None
    locRight: bool | None = None
    msgRight: bool | None = None
    sendVcardRight: bool | None = None
    recvVcardRight: bool | None = None
    keepLocalPB: bool | None = None
    vip: bool | None = None
    sipRegisterCheck: bool | None = None
    allowVideoStream: bool | None = None
    conferenceServerType: str | None = None
    conferenceServerURI: str | None = None
    monitoringMode: str | None = None
    CUS: MonitoringStateType | None = None
    HAS: MonitoringStateType | None = None
    HSS: MonitoringStateType | None = None
    HRS: MonitoringStateType | None = None
    HCS: MonitoringStateType | None = None
    SRS: MonitoringStateType | None = None
    SCS: MonitoringStateType | None = None
    CDS: MonitoringStateType | None = None
    HBS: MonitoringStateType | None = None
    BTS: MonitoringStateType | None = None
    SWS: MonitoringStateType | None = None
    credentialPw: str | None = None
    configurationDataLoaded: bool | None = None
    ppData: str | None = None
    ppProfileId: int | None = None
    fixedSipPort: int | None = None
    calculatedSipPort: int | None = None
    uidSec: int | None = None
    permanent: bool | None = None
    autoLogoutOnCharge: bool | None = None
    hotDeskingSupport: bool | None = None
    authenticateLogout: bool | None = None
    ppnOld: int | None = None
    timeStampAdmin: int | None = None
    timeStampRelation: int | None = None
    altDisplayNum: str | None = None
    sipProfileId: int | None = None
    pickupGroupNum: str | None = None
