#!/usr/bin/env python3

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .messages import Response


class OMResponseException(Exception):
    def __init__(self, response: "Response", msg: str | None = None):
        self.response = response
        if msg is None:
            msg = self.response.info
        super().__init__(msg)


exception_classes: dict[str, type[OMResponseException]] = {}


def _collect_exception_class(c: type[OMResponseException]) -> type[OMResponseException]:
    """Decorator that collects exception classes for parsing error codes."""
    exception_classes[c.__name__] = c
    return c


@_collect_exception_class
class EAreaFull(OMResponseException):
    pass


@_collect_exception_class
class EAuth(OMResponseException):
    pass


@_collect_exception_class
class EDectRegDomainInvalid(OMResponseException):
    pass


@_collect_exception_class
class EEncryptNotAllowed(OMResponseException):
    pass


@_collect_exception_class
class EExist(OMResponseException):
    pass


@_collect_exception_class
class EFailed(OMResponseException):
    pass


@_collect_exception_class
class EForbidden(OMResponseException):
    pass


@_collect_exception_class
class EInProgress(OMResponseException):
    pass


@_collect_exception_class
class EInval(OMResponseException):
    def __init__(self, response: "Response"):
        super().__init__(response, response.bad)


@_collect_exception_class
class EInvalidChars(OMResponseException):
    pass


@_collect_exception_class
class ELicense(OMResponseException):
    pass


@_collect_exception_class
class ELicenseFile(OMResponseException):
    pass


@_collect_exception_class
class ELicenseWrongInstallId(OMResponseException):
    pass


@_collect_exception_class
class EMissing(OMResponseException):
    def __init__(self, response: "Response"):
        super().__init__(response, response.bad)


@_collect_exception_class
class ENoEnt(OMResponseException):
    pass


@_collect_exception_class
class ENoMem(OMResponseException):
    pass


@_collect_exception_class
class EPerm(OMResponseException):
    pass


@_collect_exception_class
class EPwEmpty(OMResponseException):
    pass


@_collect_exception_class
class EPwSimilarToHost(OMResponseException):
    pass


@_collect_exception_class
class EPwSimilarToName(OMResponseException):
    pass


@_collect_exception_class
class EPwTooManySimilarChars(OMResponseException):
    pass


@_collect_exception_class
class EPwTooShort(OMResponseException):
    pass


@_collect_exception_class
class EPwTooSimilar(OMResponseException):
    pass


@_collect_exception_class
class EPwTooWeak(OMResponseException):
    pass


@_collect_exception_class
class EPwUnchanged(OMResponseException):
    pass


@_collect_exception_class
class ETooLong(OMResponseException):
    def __init__(self, response: "Response"):
        super().__init__(response, f"{response.bad}, maximum of {response.maxLen}")


@_collect_exception_class
class EWlanRegDomainInvalid(OMResponseException):
    pass
