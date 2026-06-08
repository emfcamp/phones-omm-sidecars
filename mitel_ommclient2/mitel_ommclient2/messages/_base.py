"""Base message types, decorators, and registries."""

from dataclasses import dataclass
from typing import Generic, TypeVar

from ..exceptions import exception_classes, OMResponseException

RespT = TypeVar("RespT", bound="Response")


# -- base classes --


class Message:
    """Base message class. Subclasses are dataclasses with typed fields."""


@dataclass
class Request(Message, Generic[RespT]):
    """Request message type."""

    seq: int | None = None


@dataclass
class Response(Message):
    """Response message type."""

    seq: int | None = None
    errCode: str | None = None
    info: str | None = None
    bad: str | None = None
    maxLen: int | None = None

    def raise_on_error(self) -> None:
        """Raise if response contains an error."""
        if self.errCode is not None:
            raise exception_classes.get(self.errCode, OMResponseException)(
                response=self
            )


@dataclass
class Event(Message):
    """Event message type. Events don't have seq or errCode."""

    pass


# -- registry --

AXI_TYPES: dict[str, type] = {}

_T = TypeVar("_T", bound=type)


def axi_parsable(c: _T) -> _T:
    """Register a message class for XML parsing."""
    AXI_TYPES[c.__name__] = c
    return c
