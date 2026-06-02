#!/usr/bin/env python3

class ChildType:
    """
        Base type class

        :param name: Name of the message
        :param attrs: Message attributes
        :param childs: Message children
    """

    FIELDS = {}

    def __init__(self, attrs={}):
        self._attrs = {}

        if self.FIELDS is not None:
            for k, v in attrs.items():
                setattr(self, k, v)
        else:
            # don't check attrs for types we do have any information
            self._attrs = attrs

    def __getattr__(self, name):
        if name in self.FIELDS.keys():
            return self._attrs.get(name)
        else:
            raise AttributeError()

    def __setattr__(self, name, value):
        if name in self.FIELDS.keys():
            if self.FIELDS[name] is not None and type(value) != self.FIELDS[name]:
                raise TypeError()
            self._attrs[name] = value
        else:
            object.__setattr__(self, name, value)

    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, repr(self._attrs))

def cast_dict_to_childtype(t, d):
    errors = {} # collect unknown keys
    for k, v in d.items():
        if k in t.FIELDS.keys():
            if t.FIELDS[k] is not None and type(v) != t.FIELDS[k]:
                d[k] = t.FIELDS[k](v)
        else:
            errors[k] = v

    if errors != {}:
        raise KeyError("The following keys are unknown for '{}': {}".format(t.__name__, errors))

    return t(d)


class EnumType:

    VALUES = [] # Allowed values

    def __init__(self, s):
        if self.VALUES is not None:
            if s in self.VALUES:
                self.value = s
            else:
                raise ValueError()
        else:
            self.value = s

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, repr(self.value))

    def __eq__(self, other):
        return isinstance(other, type(self)) and self.value == other.value


class CallForwardStateType(EnumType):
    VALUES = [
        "Off",
        "Busy",
        "NoAnswer",
        "BusyNoAnswer",
        "All",
    ]


class DECTSubscriptionModeType(EnumType):
    VALUES = [
        "Wildcard",
        "Configured",
        "Off",
    ]


class DECTSubscriptionStateType(EnumType):
    VALUES = None


class LanguageType(EnumType):
    VALUES = None


class MonitoringStateType(EnumType):
    VALUES = None


class PPRelTypeType(EnumType):
    VALUES = [
        "Fixed",
        "Dynamic",
        "Unbound",
    ]


class AccountType(ChildType):
    FIELDS = {
        "id": int,
        "username": str,
        "password": str,
        "oldPassword": str,
        "permission": None,
        "active": bool,
        "aging": None,
        "expire": int,
        "state": str,
    }


class PPDevType(ChildType):
    FIELDS = {
        "ppn": int,
        "timeStamp": int,
        "relType": PPRelTypeType,
        "uid": int,
        "ipei": str,
        "ac": str,
        "s": DECTSubscriptionStateType,
        "uak": str,
        "encrypt": bool,
        "capMessaging": bool,
        "capMessagingForInternalUse": bool,
        "capEnhLocating": bool,
        "capBluetooth": bool,
        "ethAddr": str,
        "hwType": str,
        "ppProfileCapability": bool,
        "ppDefaultProfileLoaded": bool,
        "subscribeToPARIOnly": bool,
        # undocumented
        "ommId": str,
        "ommIdAck": str,
        "timeStampAdmin": int,
        "timeStampRelation": int,
        "timeStampRoaming": int,
        "timeStampSubscription": int,
        "autoCreate": bool,
        "roaming": None, # value: 'RoamingComplete'
        "modicType": str, # value: '01'
        "locationData": str, # value: '000001000000'
        "dectIeFixedId": str,
        "subscriptionId": str,
        "ppnSec": int,
    }


class RFPStatNameType(ChildType):
    FIELDS = {
        "elemId": int,
        "group": str,
        "name": str,
    }


class RFPStatDataType(ChildType):
    FIELDS = {
        "id": int,
        "counter": str,
    }


class PPUserType(ChildType):
    FIELDS = {
        "uid": int,
        "timeStamp": int,
        "relType": PPRelTypeType,
        "ppn": int,
        "name": str,
        "num": str,
        "hierarchy1": str,
        "hierarchy2": str,
        "addId": str,
        "pin": str,
        "sipAuthId": str,
        "sipPw": str,
        "sosNum": str,
        "voiceboxNum": str,
        "manDownNum": str,
        "forwardState": CallForwardStateType,
        "forwardTime": int,
        "forwardDest": str,
        "langPP": LanguageType,
        "holdRingBackTime": int,
        "autoAnswer": str,
        "microphoneMute": str,
        "warningTone": str,
        "allowBargeIn": str,
        "callWaitingDisabled": bool,
        "external": bool,
        "trackingActive": bool,
        "locatable": bool,
        "BTlocatable": bool,
        "BTsensitivity": str,
        "locRight": bool,
        "msgRight": bool,
        "sendVcardRight": bool,
        "recvVcardRight": bool,
        "keepLocalPB": bool,
        "vip": bool,
        "sipRegisterCheck": bool,
        "allowVideoStream": bool,
        "conferenceServerType": str,
        "conferenceServerURI": str,
        "monitoringMode": str,
        "CUS": MonitoringStateType,
        "HAS": MonitoringStateType,
        "HSS": MonitoringStateType,
        "HRS": MonitoringStateType,
        "HCS": MonitoringStateType,
        "SRS": MonitoringStateType,
        "SCS": MonitoringStateType,
        "CDS": MonitoringStateType,
        "HBS": MonitoringStateType,
        "BTS": MonitoringStateType,
        "SWS": MonitoringStateType,
        "credentialPw": str,
        "configurationDataLoaded": bool,
        "ppData": str,
        "ppProfileId": int,
        "fixedSipPort": int,
        "calculatedSipPort": int,
        # undocumented
        "uidSec": int,
        "permanent": bool,
        "lang": None,
        "autoLogoutOnCharge": bool,
        "hotDeskingSupport": bool,
        "authenticateLogout": bool,
        "useSIPUserName": None,
        "useSIPUserAuthentication": None,
        "serviceUserName": None,
        "serviceAuthName": None,
        "serviceAuthPassword": None,
        "keyLockEnable": None,
        "keyLockPin": None,
        "keyLockTime": None,
        "ppnOld": int,
        "timeStampAdmin": int,
        "timeStampRelation": int,
        "altDisplayNum": str,
        "sipProfileId": int,
        "pickupGroupNum": str,
    }
