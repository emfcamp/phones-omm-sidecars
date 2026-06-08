"""Message serialization and parsing."""

import types as builtin_types
from xml.dom.minidom import Document, Element, getDOMImplementation, parseString
from typing import TypeVar, get_args, get_origin, get_type_hints

from ._base import Message, Request, Response, AXI_TYPES

RespT = TypeVar("RespT", bound="Response")


# -- type helpers --


def _strip_none(annotation: type) -> type:
    """Extract base type from X | None -> X."""
    if get_origin(annotation) is builtin_types.UnionType:
        args = get_args(annotation)
        return next(arg for arg in args if arg is not type(None))
    return annotation


def _get_fields_and_childs(cls: type) -> tuple[dict[str, type], dict[str, type]]:
    """Get fields and children from typed class attributes.

    Fields are single values (attributes), children are lists (child elements).
    """
    fields: dict[str, type] = {}
    childs: dict[str, type] = {}
    for name, annotation in get_type_hints(cls).items():
        if name.startswith("_"):
            continue
        base = _strip_none(annotation)
        origin = get_origin(base)
        if origin is list:
            childs[name] = get_args(base)[0]
        else:
            fields[name] = base
    return fields, childs


def get_response_type(cls: "type[Request[RespT]]") -> "type[RespT]":
    """Extract the Response type from a Request[RespT] Generic. Runtime only."""
    return cls.__orig_bases__[0].__args__[0]  # type: ignore[reportUnknownMemberType]


# -- serialization --


def _serialize_element(
    doc: Document, msg: object, tag_name: str | None = None
) -> Element:
    """Recursively serialize a typed object into an XML element."""
    fields, childs = _get_fields_and_childs(type(msg))
    element = doc.createElement(tag_name or type(msg).__name__)

    for k in fields:
        v = getattr(msg, k, None)
        if v is not None:
            element.setAttribute(k, str(v).lower() if isinstance(v, bool) else str(v))

    for child_name in childs:
        children = getattr(msg, child_name, [])
        for child_obj in children:
            element.appendChild(_serialize_element(doc, child_obj, tag_name=child_name))

    return element


def construct(msg: Message) -> str:
    """Build XML message DOM and return as string."""
    impl = getDOMImplementation()
    doc = impl.createDocument(None, type(msg).__name__, None)
    root = doc.documentElement
    assert root is not None

    fields, childs = _get_fields_and_childs(type(msg))

    for k in fields:
        v = getattr(msg, k, None)
        if v is not None:
            root.setAttribute(k, str(v).lower() if isinstance(v, bool) else str(v))

    for child_name in childs:
        children = getattr(msg, child_name, [])
        for child_obj in children:
            root.appendChild(_serialize_element(doc, child_obj, tag_name=child_name))

    return root.toxml()


# -- parsing --


def _parse_attrs(element: Element, fields: dict[str, type]) -> dict[str, object]:
    """Parse XML attributes into a kwargs dict. Unknown fields are dropped."""
    kwargs: dict[str, object] = {}
    for i in range(element.attributes.length):
        item = element.attributes.item(i)
        if item is None:
            continue
        field_type = fields.get(item.name)
        if field_type is bool:
            if item.value not in ("0", "1", "true", "false"):
                raise TypeError(f"Invalid bool value for {item.name}: {item.value!r}")
            kwargs[item.name] = item.value in ("1", "true")
        elif field_type is not None:
            kwargs[item.name] = field_type(item.value)
    return kwargs


def _parse_element(element: Element, cls: type) -> object:
    """Recursively parse an XML element into a typed object."""
    fields, childs = _get_fields_and_childs(cls)
    kwargs = _parse_attrs(element, fields)

    child_lists: dict[str, list[object]] = {}
    child = element.firstChild
    while child is not None:
        if isinstance(child, Element):
            child_name = child.tagName
            child_cls = childs.get(child_name)
            if child_cls is not None:
                child_obj = _parse_element(child, child_cls)
                child_lists.setdefault(child_name, []).append(child_obj)
        child = child.nextSibling

    return cls(**kwargs, **child_lists)


def parse(message: str) -> Message:
    """Parse XML message into a Response object."""
    doc = parseString(message)
    root = doc.documentElement
    assert root is not None

    name = root.tagName
    response_cls = AXI_TYPES[name]
    result = _parse_element(root, response_cls)
    assert isinstance(result, Message)
    return result
