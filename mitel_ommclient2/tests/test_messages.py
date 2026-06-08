"""Tests for message parsing and serialization.

Covers: type conversion, bool handling, optional fields, child elements,
error responses, edge cases, and round-trip consistency.
"""

import pytest
from mitel_ommclient2 import types
from mitel_ommclient2.messages import (
    Ping,
    PingResp,
    GetPPUser,
    GetPPUserResp,
    Open,
    OpenResp,
    construct,
    parse,
)
from mitel_ommclient2 import exceptions


# -- parsing: simple types --


class TestParseSimpleTypes:
    def test_int_field(self):
        r = parse('<PingResp timeStamp="42"/>')
        assert r.timeStamp == 42

    def test_str_field(self):
        r = parse('<OpenResp ommVersion="3.0 RC1"/>')
        assert r.ommVersion == "3.0 RC1"

    def test_optional_field_absent(self):
        r = parse("<PingResp/>")
        assert r.timeStamp is None

    def test_optional_field_present(self):
        r = parse('<PingResp timeStamp="99"/>')
        assert r.timeStamp == 99


# -- parsing: booleans --


class TestParseBooleans:
    def test_bool_true_1(self):
        r = parse('<OpenResp EULAConfirm="1"/>')
        assert r.EULAConfirm is True

    def test_bool_true_true(self):
        r = parse('<OpenResp EULAConfirm="true"/>')
        assert r.EULAConfirm is True

    def test_bool_false_0(self):
        r = parse('<OpenResp EULAConfirm="0"/>')
        assert r.EULAConfirm is False

    def test_bool_false_false(self):
        r = parse('<OpenResp EULAConfirm="false"/>')
        assert r.EULAConfirm is False

    def test_bool_invalid_yes(self):
        """Non-standard bool values should error, not silently become False."""
        with pytest.raises(TypeError):
            parse('<OpenResp EULAConfirm="yes"/>')

    def test_bool_invalid_no(self):
        with pytest.raises(TypeError):
            parse('<OpenResp EULAConfirm="no"/>')

    def test_bool_invalid_number(self):
        with pytest.raises(TypeError):
            parse('<OpenResp EULAConfirm="2"/>')


# -- parsing: type conversion errors --


class TestParseTypeErrors:
    def test_string_for_int_field(self):
        with pytest.raises(ValueError):
            parse('<PingResp timeStamp="abc"/>')

    def test_empty_string_for_int_field(self):
        with pytest.raises(ValueError):
            parse('<PingResp timeStamp=""/>')

    def test_unknown_field_dropped(self):
        """Unknown fields are silently dropped — only typed fields are kept."""
        r = parse('<PingResp unknownField="hello"/>')
        assert not hasattr(r, "unknownField")


# -- parsing: child elements --


class TestParseChildren:
    def test_single_child(self):
        r = parse('<EventPPDevCnf><pp ppn="5"/></EventPPDevCnf>')
        assert len(r.pp) == 1
        assert r.pp[0].ppn == 5

    def test_multiple_children(self):
        r = parse('<GetPPUserResp><user uid="1"/><user uid="2"/></GetPPUserResp>')
        assert len(r.user) == 2
        assert r.user[0].uid == 1
        assert r.user[1].uid == 2

    def test_no_children(self):
        r = parse("<GetPPUserResp/>")
        assert r.user == []

    def test_child_with_multiple_fields(self):
        r = parse('<EventPPDevCnf><pp ppn="5" uid="3" ipei="12345"/></EventPPDevCnf>')
        assert r.pp[0].ppn == 5
        assert r.pp[0].uid == 3
        assert r.pp[0].ipei == "12345"

    def test_child_bool_field(self):
        r = parse('<EventPPDevCnf deleted="1"><pp ppn="5"/></EventPPDevCnf>')
        assert r.deleted is True

    def test_child_and_field_together(self):
        r = parse('<EventPPDevCnf deleted="0"><pp ppn="5"/></EventPPDevCnf>')
        assert r.deleted is False
        assert len(r.pp) == 1


# -- parsing: error responses --


class TestParseErrorResponses:
    def test_error_response_has_errcode(self):
        r = parse('<PingResp errCode="EAuth"/>')
        assert r.errCode == "EAuth"

    def test_error_response_with_info(self):
        r = parse('<PingResp errCode="EAuth" info="bad password"/>')
        assert r.errCode == "EAuth"
        assert r.info == "bad password"

    def test_error_response_fields_default(self):
        """Error responses don't include success fields — they default."""
        r = parse('<PingResp errCode="EAuth"/>')
        assert r.timeStamp is None
        assert r.seq is None

    def test_raise_on_error(self):
        r = parse('<PingResp errCode="EAuth"/>')
        with pytest.raises(exceptions.EAuth):
            r.raise_on_error()

    def test_raise_on_error_with_info(self):
        r = parse('<PingResp errCode="EFailed" info="standby"/>')
        with pytest.raises(exceptions.EFailed) as exc_info:
            r.raise_on_error()
        assert "standby" in str(exc_info.value)

    def test_no_error_when_errcode_absent(self):
        r = parse('<PingResp timeStamp="42"/>')
        r.raise_on_error()  # should not raise

    def test_error_response_with_seq(self):
        r = parse('<PingResp seq="5" errCode="EAuth"/>')
        assert r.seq == 5
        assert r.errCode == "EAuth"


# -- parsing: edge cases --


class TestParseEdgeCases:
    def test_unknown_message_type_raises(self):
        """Unknown message types are not registered — KeyError."""
        with pytest.raises(KeyError):
            parse('<UnknownMessage field="val"/>')

    def test_empty_element(self):
        r = parse("<PingResp/>")
        assert r.timeStamp is None

    def test_element_with_only_unknown_fields(self):
        """Unknown fields are silently dropped."""
        r = parse('<PingResp foo="bar" baz="123"/>')
        assert not hasattr(r, "foo")
        assert not hasattr(r, "baz")

    def test_nested_unknown_child(self):
        """Unknown child elements are ignored."""
        r = parse('<PingResp><unknownChild field="val"/></PingResp>')
        # unknown child should not cause error, just be ignored
        assert r.timeStamp is None

    def test_whitespace_in_values(self):
        r = parse('<OpenResp ommVersion="  3.0 RC1  "/>')
        assert r.ommVersion == "  3.0 RC1  "


# -- serialization --


class TestConstruct:
    def test_simple_fields(self):
        p = Ping(timeStamp=42)
        xml = construct(p)
        assert 'timeStamp="42"' in xml

    def test_bool_field_true(self):
        o = Open(UserDeviceSyncClient="true")
        xml = construct(o)
        assert 'UserDeviceSyncClient="true"' in xml

    def test_none_fields_omitted(self):
        p = Ping()
        xml = construct(p)
        assert "timeStamp" not in xml

    def test_child_elements(self):
        u = GetPPUserResp()
        u.user.append(types.PPUserType(uid=42))
        xml = construct(u)
        assert "<user" in xml
        assert 'uid="42"' in xml

    def test_root_element_name(self):
        p = Ping()
        xml = construct(p)
        assert xml.startswith("<Ping")

    def test_empty_message(self):
        p = Ping()
        xml = construct(p)
        assert "<Ping" in xml
        assert "/>" in xml or "></Ping>" in xml


# -- round-trip --


class TestRoundTrip:
    def test_parse_construct_parse(self):
        """Parse → construct → parse should preserve data."""
        original = '<PingResp timeStamp="42"/>'
        r1 = parse(original)
        xml = construct(r1)
        r2 = parse(xml)
        assert r1.timeStamp == r2.timeStamp

    def test_round_trip_with_child(self):
        original = '<EventPPDevCnf deleted="1"><pp ppn="5" uid="3"/></EventPPDevCnf>'
        r1 = parse(original)
        xml = construct(r1)
        r2 = parse(xml)
        assert r1.deleted == r2.deleted
        assert r1.pp[0].ppn == r2.pp[0].ppn
        assert r1.pp[0].uid == r2.pp[0].uid


# -- get_response_type --


class TestGetResponseType:
    def test_extracts_response_type(self):
        from mitel_ommclient2.messages import get_response_type

        assert get_response_type(Ping) is PingResp
        assert get_response_type(GetPPUser) is GetPPUserResp
        assert get_response_type(Open) is OpenResp
