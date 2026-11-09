"""Unit tests for api.get_balance and the Balance model (mocked HTTP)."""

from __future__ import annotations

from unittest.mock import MagicMock

from lxml import etree

from drebedengi import DrebedengiAPI
from drebedengi.model import Balance
from drebedengi.utils import xmlmap_to_model


NS = 'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema"'


def _balance_item_xml(
    *,
    place_id: str = "12345",
    place_name: str = "Основная карта",
    sum_: str = "1234567",
    currency_name: str | None = "₽",
    parent_id: str = "17900001",
    is_credit_card: str | None = "t",
) -> etree.Element:
    """One getBalance ns2:Map item; None drops the optional key entirely."""
    def kv(key: str, value: str | None) -> str:
        if value is None:
            return ""
        return (
            f"<item><key>{key}</key>"
            f"<value xsi:type=\"xsd:string\">{value}</value></item>"
        )

    parts = [
        kv("place_id", place_id),
        kv("place_name", place_name),
        kv("sum", sum_),
        kv("currency_name", currency_name),
        kv("parent_id", parent_id),
        kv("is_credit_card", is_credit_card),
    ]
    src = f'<item {NS}>' + "".join(parts) + "</item>"
    return etree.fromstring(src)


BALANCE_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"
 xmlns:ns1="urn:ddengi"
 xmlns:ns2="http://xml.apache.org/xml-soap"
 xmlns:SOAP-ENC="http://schemas.xmlsoap.org/soap/encoding/"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
 xmlns:xsd="http://www.w3.org/2001/XMLSchema">
<SOAP-ENV:Body>
<ns1:getBalanceResponse>
<getBalanceReturn SOAP-ENC:arrayType="ns2:Map[2]" xsi:type="SOAP-ENC:Array">
<!-- leaf credit-card account inside folder 17900001: 12345.67 rub in kopecks -->
<item xsi:type="ns2:Map">
<item><key xsi:type="xsd:string">place_id</key><value xsi:type="xsd:string">12345</value></item>
<item><key xsi:type="xsd:string">place_name</key><value xsi:type="xsd:string">Основная карта</value></item>
<item><key xsi:type="xsd:string">sum</key><value xsi:type="xsd:string">1234567</value></item>
<item><key xsi:type="xsd:string">currency_name</key><value xsi:type="xsd:string">₽</value></item>
<item><key xsi:type="xsd:string">parent_id</key><value xsi:type="xsd:string">17900001</value></item>
<item><key xsi:type="xsd:string">is_credit_card</key><value xsi:type="xsd:string">t</value></item>
</item>
<!-- leaf cash account: no currency_name / is_credit_card keys -->
<item xsi:type="ns2:Map">
<item><key xsi:type="xsd:string">place_id</key><value xsi:type="xsd:string">12400</value></item>
<item><key xsi:type="xsd:string">place_name</key><value xsi:type="xsd:string">Наличные</value></item>
<item><key xsi:type="xsd:string">sum</key><value xsi:type="xsd:string">9900</value></item>
<item><key xsi:type="xsd:string">parent_id</key><value xsi:type="xsd:string">-1</value></item>
</item>
</getBalanceReturn>
</ns1:getBalanceResponse>
</SOAP-ENV:Body>
</SOAP-ENV:Envelope>""".encode("utf-8")


def _mk_api_balance(content: bytes = BALANCE_RESPONSE) -> DrebedengiAPI:
    a = DrebedengiAPI.__new__(DrebedengiAPI)
    a.api_key, a.login, a.password = "k", "l", "p"
    a.soap_url, a.strict = "fake", True
    fake_client = MagicMock()
    fake_response = MagicMock()
    fake_response.ok = True
    fake_response.status_code = 200
    fake_response.content = content
    fake_client.service.getBalance.return_value = fake_response
    fake_client.settings.return_value.__enter__ = lambda self: None
    fake_client.settings.return_value.__exit__ = lambda *args: None
    a.client = fake_client
    return a


# ---------------------------------------------------------------------------
# Balance model parsing (XML fixture)
# ---------------------------------------------------------------------------

def test_balance_model_parses_full_item() -> None:
    item = _balance_item_xml()
    b = xmlmap_to_model(item, Balance)
    assert b.place_id == 12345
    assert b.place_name == "Основная карта"
    assert b.amount == 1234567  # kopecks: "sum" maps to amount
    assert b.currency_name == "₽"
    assert b.parent_id == 17900001
    assert b.is_credit_card is True


def test_balance_model_optional_keys_absent() -> None:
    item = _balance_item_xml(currency_name=None, is_credit_card=None, parent_id=None)
    b = xmlmap_to_model(item, Balance)
    assert b.currency_name is None
    assert b.is_credit_card is None
    assert b.parent_id == -1


def test_balance_model_credit_card_false() -> None:
    b = xmlmap_to_model(_balance_item_xml(is_credit_card="f"), Balance)
    assert b.is_credit_card is False


# ---------------------------------------------------------------------------
# api.get_balance (mocked SOAP)
# ---------------------------------------------------------------------------

def test_get_balance_parses_two_items() -> None:
    api = _mk_api_balance()
    result = api.get_balance()
    assert len(result) == 2
    assert all(isinstance(b, Balance) for b in result)


def test_get_balance_first_item_fields() -> None:
    api = _mk_api_balance()
    b = api.get_balance()[0]
    assert b.place_id == 12345
    assert b.place_name == "Основная карта"
    assert b.amount == 1234567
    assert b.currency_name == "₽"
    assert b.parent_id == 17900001
    assert b.is_credit_card is True


def test_get_balance_optional_fields_absent() -> None:
    api = _mk_api_balance()
    b = api.get_balance()[1]
    assert b.place_id == 12400
    assert b.place_name == "Наличные"
    assert b.amount == 9900
    assert b.currency_name is None
    assert b.is_credit_card is None
    assert b.parent_id == -1


def test_get_balance_passes_credentials() -> None:
    api = _mk_api_balance()
    api.get_balance()
    args = api.client.service.getBalance.call_args.args
    assert args == ("k", "l", "p")


def test_get_balance_params_is_skipvalue() -> None:
    """params is always SkipValue: the server rejects relative_date here."""
    import zeep

    api = _mk_api_balance()
    api.get_balance()
    call_kwargs = api.client.service.getBalance.call_args.kwargs
    assert call_kwargs.get("params") is zeep.xsd.SkipValue
