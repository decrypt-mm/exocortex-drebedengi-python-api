"""Unit tests for api.set_check_list (mocked HTTP)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from drebedengi import DrebedengiAPI, DrebedengiAPIError


FAKE_OK_RESPONSE = (
    b'<?xml version="1.0" encoding="UTF-8"?>'
    b'<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"'
    b' xmlns:ns1="urn:ddengi"'
    b' xmlns:ns2="http://xml.apache.org/xml-soap"'
    b' xmlns:SOAP-ENC="http://schemas.xmlsoap.org/soap/encoding/"'
    b' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
    b' xmlns:xsd="http://www.w3.org/2001/XMLSchema">'
    b"<SOAP-ENV:Body>"
    b"<ns1:setCheckListResponse>"
    b'<setCheckListReturn SOAP-ENC:arrayType="ns2:Map[1]" xsi:type="SOAP-ENC:Array">'
    b'<item xsi:type="ns2:Map">'
    b'<item><key xsi:type="xsd:string">server_id</key>'
    b'<value xsi:type="xsd:string">8108127</value></item>'
    b'<item><key xsi:type="xsd:string">client_id</key>'
    b'<value xsi:type="xsd:int">1</value></item>'
    b"</item>"
    b"</setCheckListReturn>"
    b"</ns1:setCheckListResponse>"
    b"</SOAP-ENV:Body>"
    b"</SOAP-ENV:Envelope>"
)

FAKE_FAULT_RESPONSE = (
    b'<?xml version="1.0" encoding="UTF-8"?>'
    b'<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">'
    b"<SOAP-ENV:Body>"
    b"<SOAP-ENV:Fault>"
    b"<faultcode>SOAP-ENV:Client</faultcode>"
    b"<faultstring>Invalid check data</faultstring>"
    b"</SOAP-ENV:Fault>"
    b"</SOAP-ENV:Body>"
    b"</SOAP-ENV:Envelope>"
)

CLEAN_QR = "t=20261002T1909&s=441.00&fn=7380440903113332&i=153052&fp=2969220808&n=1"


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch) -> DrebedengiAPI:
    a = DrebedengiAPI.__new__(DrebedengiAPI)
    a.api_key = "k"
    a.login = "l"
    a.password = "p"
    a.soap_url = "fake"
    a.strict = True
    fake_client = MagicMock()
    fake_response = MagicMock()
    fake_response.ok = True
    fake_response.status_code = 200
    fake_response.content = FAKE_OK_RESPONSE
    fake_client.service.setCheckList.return_value = fake_response
    fake_client.settings.return_value.__enter__ = lambda self: None
    fake_client.settings.return_value.__exit__ = lambda *args: None
    a.client = fake_client
    return a


def _payload_of(list_xml) -> dict:
    """The serialized SOAP Array of one ns2:Map -> flat {key: value}."""
    entries = list_xml.item[0].item
    return {e["key"].value: e["value"].value for e in entries}


def test_set_check_list_parses_server_response(api: DrebedengiAPI) -> None:
    result = api.set_check_list([{"ext": CLEAN_QR, "client_id": 1}])
    assert result == [{"server_id": "8108127", "client_id": "1"}]


def test_set_check_list_minimal_ext_only_payload(api: DrebedengiAPI) -> None:
    """Spike form 1: {'ext': qr} with no id keys — passed through as-is."""
    api.set_check_list([{"ext": CLEAN_QR}])
    call = api.client.service.setCheckList.call_args
    assert call.args == ("k", "l", "p")
    assert _payload_of(call.kwargs["list"]) == {"ext": CLEAN_QR}


def test_set_check_list_passes_state_through(api: DrebedengiAPI) -> None:
    """Spike form 3: state and arbitrary extra fields are not filtered out."""
    api.set_check_list([{"ext": CLEAN_QR, "client_id": 7, "state": 0}])
    assert _payload_of(api.client.service.setCheckList.call_args.kwargs["list"]) == {
        "ext": CLEAN_QR, "client_id": 7, "state": 0}


def test_set_check_list_does_not_mutate_caller_dict(api: DrebedengiAPI) -> None:
    check = {"ext": CLEAN_QR}
    api.set_check_list([check])
    assert check == {"ext": CLEAN_QR}


def test_set_check_list_empty_returns_empty(api: DrebedengiAPI) -> None:
    assert api.set_check_list([]) == []
    api.client.service.setCheckList.assert_not_called()


def test_set_check_list_soap_fault_raises(api: DrebedengiAPI) -> None:
    fake_response = MagicMock()
    fake_response.ok = True
    fake_response.status_code = 200
    fake_response.content = FAKE_FAULT_RESPONSE
    fake_response.text = "fault"
    api.client.service.setCheckList.return_value = fake_response
    with pytest.raises(DrebedengiAPIError, match="Invalid check data"):
        api.set_check_list([{"ext": CLEAN_QR}])


def test_set_check_list_network_error_raises(api: DrebedengiAPI) -> None:
    fake_response = MagicMock()
    fake_response.ok = False
    fake_response.status_code = 500
    fake_response.text = "boom"
    api.client.service.setCheckList.return_value = fake_response
    with pytest.raises(DrebedengiAPIError, match="Network error"):
        api.set_check_list([{"ext": CLEAN_QR}])
