"""Unit tests for api.get_user_id_by_login (mocked HTTP)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from drebedengi import DrebedengiAPI, DrebedengiAPIError


FAKE_OK_RESPONSE = (
    b'<?xml version="1.0" encoding="UTF-8"?>'
    b'<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"'
    b' xmlns:ns1="urn:ddengi">'
    b"<SOAP-ENV:Body>"
    b"<ns1:getUserIdByLoginResponse>"
    b"<getUserIdByLoginReturn xsi:type=\"xsd:string\""
    b" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\">1000000308143"
    b"</getUserIdByLoginReturn>"
    b"</ns1:getUserIdByLoginResponse>"
    b"</SOAP-ENV:Body>"
    b"</SOAP-ENV:Envelope>"
)

FAKE_GARBAGE_RESPONSE = (
    b'<?xml version="1.0" encoding="UTF-8"?>'
    b'<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"'
    b' xmlns:ns1="urn:ddengi">'
    b"<SOAP-ENV:Body>"
    b"<ns1:getUserIdByLoginResponse>"
    b"<getUserIdByLoginReturn>not-a-number</getUserIdByLoginReturn>"
    b"</ns1:getUserIdByLoginResponse>"
    b"</SOAP-ENV:Body>"
    b"</SOAP-ENV:Envelope>"
)


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
    fake_client.service.getUserIdByLogin.return_value = fake_response
    fake_client.settings.return_value.__enter__ = lambda self: None
    fake_client.settings.return_value.__exit__ = lambda *args: None
    a.client = fake_client
    return a


def test_returns_int_user_id(api: DrebedengiAPI) -> None:
    assert api.get_user_id_by_login() == 1000000308143


def test_calls_with_credentials(api: DrebedengiAPI) -> None:
    api.get_user_id_by_login()
    assert api.client.service.getUserIdByLogin.call_args.args == ("k", "l", "p")


def test_non_numeric_payload_raises(api: DrebedengiAPI) -> None:
    api.client.service.getUserIdByLogin.return_value.content = FAKE_GARBAGE_RESPONSE
    with pytest.raises(DrebedengiAPIError):
        api.get_user_id_by_login()
