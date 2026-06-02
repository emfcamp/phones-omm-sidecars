#!/usr/bin/env python3

from xml.dom.minidom import getDOMImplementation, parseString

from ..exceptions import exception_classes, OMResponseException
from ..types import cast_dict_to_childtype


class Message:
    """
        Base message class

        :param name: Name of the message
        :param attrs: Message attributes
        :param childs: Message children
    """

    # Fields defined by the base type class
    BASE_FIELDS = {}
    # Fields defined by subclasses
    FIELDS = {}
    # Child types
    CHILDS = {}
    # Fields dicts consist of the field name as name and the field type as value
    # Use None if the field type is unknown, any type is allowed then


    class Childs:
        """
            Contains message childs
        """

        CHILDS = {}

        def __init__(self, child_types, child_dict):
            self.CHILDS = child_types
            self._child_dict = child_dict

        def __getattr__(self, name):
            if name in self.CHILDS.keys():
                return self._child_dict.get(name)
            else:
                raise AttributeError()

        def __setattr__(self, name, value):
            if name in self.CHILDS.keys():
                if not isinstance(value, list):
                    raise TypeError()
                for v in value:
                    if self.CHILDS[name] is not None and type(v) != self.CHILDS[name]:
                        raise TypeError()
                self._child_dict[name] = value
            else:
                object.__setattr__(self, name, value)


    def __init__(self, name=None, attrs={}, childs={}):
        self.name = name
        if not self.name:
            self.name = self.__class__.__name__
        self._attrs = {} | attrs
        self._childs = {} | childs
        self.childs = self.Childs(self.CHILDS, self._childs)

    def __getattr__(self, name):
        fields = self.FIELDS | self.BASE_FIELDS
        if name in fields.keys():
            return self._attrs.get(name)
        else:
            raise AttributeError()

    def __setattr__(self, name, value):
        fields = self.FIELDS | self.BASE_FIELDS
        if name in fields.keys():
            if fields[name] is not None and type(value) != fields[name]:
                raise TypeError()
            self._attrs[name] = value
        else:
            object.__setattr__(self, name, value)

    def __repr__(self):
        return "{}({}, {}, {})".format(self.__class__.__name__, repr(self.name), repr(self._attrs), repr(self._childs))


class Request(Message):
    """
        Request message type class
    """

    BASE_FIELDS = {
        "seq": int,
    }


class Response(Message):
    """
        Response message type class
    """

    BASE_FIELDS = {
        "seq": int,
        "errCode": None,
        "info": None,
        "bad": None,
        "maxLen": None,
    }

    def raise_on_error(self):
        """
            Raises an exception if the response contains an error.

            Usage::

                >>> try:
                >>>     r.raise_on_error()
                >>> except mitel_ommclient2.exceptions.EAuth as e:
                >>>     print("We don't care about authentication!")

            See children of :class:`mitel_ommclient2.exceptions.OMResponseException` for all possible exceptions.
        """

        if self.errCode is not None:
            raise exception_classes.get(self.errCode, OMResponseException)(response=self)


REQUEST_TYPES = {}
RESPONSE_TYPES = {}

def request_type(c):
    REQUEST_TYPES[c.__name__] = c
    return c

def response_type(c):
    RESPONSE_TYPES[c.__name__] = c
    return c

from .createppuser import CreatePPUser, CreatePPUserResp
from .deleteppdev import DeletePPDev, DeletePPDevResp
from .deleteppuser import DeletePPUser, DeletePPUserResp
from .getaccount import GetAccount, GetAccountResp
from .getdectauthcode import GetDECTAuthCode, GetDECTAuthCodeResp
from .getdectsubscriptionmode import GetDECTSubscriptionMode, GetDECTSubscriptionModeResp
from .getdevautocreate import GetDevAutoCreate, GetDevAutoCreateResp
from .getppdev import GetPPDev, GetPPDevResp
from .getppdevsummary import GetPPDevSummary, GetPPDevSummaryResp
from .getppuser import GetPPUser, GetPPUserResp
from .getppusersummary import GetPPUserSummary, GetPPUserSummaryResp
from .getpublickey import GetPublicKey, GetPublicKeyResp
from .getrfp import GetRFP, GetRFPResp
from .getrfpsummary import GetRFPSummary, GetRFPSummaryResp
from .getrfpstatistic import GetRFPStatistic, GetRFPStatisticResp
from .getrfpstatisticconfig import GetRFPStatisticConfig, GetRFPStatisticConfigResp
from .open import Open, OpenResp
from .ping import Ping, PingResp
from .setdectauthcode import SetDECTAuthCode, SetDECTAuthCodeResp
from .setdectsubscriptionmode import SetDECTSubscriptionMode, SetDECTSubscriptionModeResp
from .setdevautocreate import SetDevAutoCreate, SetDevAutoCreateResp
from .setpp import SetPP, SetPPResp
from .setppuser import SetPPUser, SetPPUserResp
from .setppuserdevrelation import SetPPUserDevRelation, SetPPUserDevRelationResp

def construct(request):
    """
        Builds the XML message DOM and returns as string
    """
    impl = getDOMImplementation()
    message = impl.createDocument(None, request.name, None)
    root = message.documentElement

    for k, v in request._attrs.items():
        root.setAttribute(str(k), str(v))


    for child_name, child_list in request._childs.items():
        if child_list is not None:
            for child_list_item in child_list:
                child = message.createElement(child_name)
                for child_item_key, child_item_value in child_list_item._attrs.items():
                    child.setAttribute(str(child_item_key), str(child_item_value))
                root.appendChild(child)
    return root.toxml()

def parse(message):
    message = parseString(message)
    root = message.documentElement

    name = root.tagName
    attrs = {}
    childs = {}

    response_type = RESPONSE_TYPES.get(name)
    fields = response_type.FIELDS | response_type.BASE_FIELDS

    for i in range(0, root.attributes.length):
        item = root.attributes.item(i)
        if fields.get(item.name) is not None:
            if fields[item.name] is bool and type(item.value) is not bool:
                if item.value not in ["1", "0", "true", "false"]:
                    raise TypeError(f'boolean type is expected to be either True, False, "1", "0", "true" or "false". Found {item.value} of type {type(item.value)}')
                attrs[item.name] = item.value in ["1", "true"]
            else:
                attrs[item.name] = fields[item.name](item.value)
        else:
            attrs[item.name] = item.value

    child = root.firstChild
    while child is not None:
        new_child = {}
        for i in range(0, child.attributes.length):
            item = child.attributes.item(i)
            new_child[item.name] = item.value

        childname = child.tagName

        # cast dict into child type
        if response_type.CHILDS.get(childname) is not None:
            new_child = cast_dict_to_childtype(response_type.CHILDS[childname], new_child)

        if childname in childs:
            childs[childname].append(new_child)
        else:
            childs[childname] = [new_child]

        child = child.nextSibling


    return response_type(name, attrs, childs)
