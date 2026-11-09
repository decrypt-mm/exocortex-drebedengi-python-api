"""Unit tests for Account parsing: unknown object types (folders, type=9) and
the is_credit_card / parent_id fields (mocked HTTP for the api-level tests)."""

from __future__ import annotations

from unittest.mock import MagicMock

from lxml import etree

from drebedengi import DrebedengiAPI
from drebedengi.model import Account, ObjectType
from drebedengi.utils import xmlmap_to_model


NS = 'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema"'


def _account_item_xml(
    *,
    id_: str = "17909584",
    type_: str = "4",
    name: str = "Совкомбанк Дебетовая",
    parent_id: str | None = "17900001",
    is_credit_card: str | None = "f",
) -> etree.Element:
    """One getPlaceList ns2:Map item; None drops the optional key entirely."""
    def kv(key: str, value: str | None) -> str:
        if value is None:
            return ""
        return (
            f"<item><key>{key}</key>"
            f"<value xsi:type=\"xsd:string\">{value}</value></item>"
        )

    parts = [
        kv("id", id_),
        kv("budget_family_id", "283054"),
        kv("type", type_),
        kv("name", name),
        kv("is_hidden", "f"),
        kv("is_autohide", "f"),
        kv("is_for_duty", "f"),
        kv("sort", "100"),
        kv("purse_of_nuid", None),
        kv("icon_id", None),
        kv("parent_id", parent_id),
        kv("is_credit_card", is_credit_card),
    ]
    src = f'<item {NS}>' + "".join(parts) + "</item>"
    return etree.fromstring(src)


ACCOUNTS_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"
 xmlns:ns1="urn:ddengi"
 xmlns:ns2="http://xml.apache.org/xml-soap"
 xmlns:SOAP-ENC="http://schemas.xmlsoap.org/soap/encoding/"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
 xmlns:xsd="http://www.w3.org/2001/XMLSchema">
<SOAP-ENV:Body>
<ns1:getPlaceListResponse>
<getPlaceListReturn SOAP-ENC:arrayType="ns2:Map[2]" xsi:type="SOAP-ENC:Array">
<!-- regular account (type=4) inside folder 17900001 -->
<item xsi:type="ns2:Map">
<item><key xsi:type="xsd:string">id</key><value xsi:type="xsd:string">17909584</value></item>
<item><key xsi:type="xsd:string">budget_family_id</key><value xsi:type="xsd:string">283054</value></item>
<item><key xsi:type="xsd:string">type</key><value xsi:type="xsd:string">4</value></item>
<item><key xsi:type="xsd:string">name</key><value xsi:type="xsd:string">Совкомбанк Дебетовая</value></item>
<item><key xsi:type="xsd:string">is_hidden</key><value xsi:type="xsd:string">f</value></item>
<item><key xsi:type="xsd:string">is_autohide</key><value xsi:type="xsd:string">f</value></item>
<item><key xsi:type="xsd:string">is_for_duty</key><value xsi:type="xsd:string">f</value></item>
<item><key xsi:type="xsd:string">sort</key><value xsi:type="xsd:string">100</value></item>
<item><key xsi:type="xsd:string">parent_id</key><value xsi:type="xsd:string">17900001</value></item>
<item><key xsi:type="xsd:string">is_credit_card</key><value xsi:type="xsd:string">f</value></item>
</item>
<!-- account folder (type=9): no is_credit_card key -->
<item xsi:type="ns2:Map">
<item><key xsi:type="xsd:string">id</key><value xsi:type="xsd:string">17900001</value></item>
<item><key xsi:type="xsd:string">budget_family_id</key><value xsi:type="xsd:string">283054</value></item>
<item><key xsi:type="xsd:string">type</key><value xsi:type="xsd:string">9</value></item>
<item><key xsi:type="xsd:string">name</key><value xsi:type="xsd:string">Банк</value></item>
<item><key xsi:type="xsd:string">is_hidden</key><value xsi:type="xsd:string">f</value></item>
<item><key xsi:type="xsd:string">is_autohide</key><value xsi:type="xsd:string">f</value></item>
<item><key xsi:type="xsd:string">is_for_duty</key><value xsi:type="xsd:string">f</value></item>
<item><key xsi:type="xsd:string">sort</key><value xsi:type="xsd:string">10</value></item>
<item><key xsi:type="xsd:string">parent_id</key><value xsi:type="xsd:string">-1</value></item>
</item>
</getPlaceListReturn>
</ns1:getPlaceListResponse>
</SOAP-ENV:Body>
</SOAP-ENV:Envelope>""".encode("utf-8")


def _mk_api_accounts(content: bytes = ACCOUNTS_RESPONSE) -> DrebedengiAPI:
    a = DrebedengiAPI.__new__(DrebedengiAPI)
    a.api_key, a.login, a.password = "k", "l", "p"
    a.soap_url, a.strict = "fake", True
    fake_client = MagicMock()
    fake_response = MagicMock()
    fake_response.ok = True
    fake_response.status_code = 200
    fake_response.content = content
    fake_client.service.getPlaceList.return_value = fake_response
    fake_client.settings.return_value.__enter__ = lambda self: None
    fake_client.settings.return_value.__exit__ = lambda *args: None
    a.client = fake_client
    return a


# ---------------------------------------------------------------------------
# object_type conversion
# ---------------------------------------------------------------------------

def test_account_known_type_resolves_to_enum() -> None:
    acc = xmlmap_to_model(_account_item_xml(type_="4"), Account)
    assert acc.object_type is ObjectType.ACCOUNT


def test_account_folder_type9_converts() -> None:
    """Account folder (type=9) parses as raw int – no enum member, no crash."""
    acc = xmlmap_to_model(_account_item_xml(type_="9", name="Банк"), Account)
    assert acc.object_type == 9
    assert isinstance(acc.object_type, int)
    assert not isinstance(acc.object_type, ObjectType)
    assert acc.name == "Банк"


def test_account_unknown_type_falls_back_to_int() -> None:
    acc = xmlmap_to_model(_account_item_xml(type_="99"), Account)
    assert acc.object_type == 99
    assert isinstance(acc.object_type, int)
    assert not isinstance(acc.object_type, ObjectType)


# ---------------------------------------------------------------------------
# is_credit_card / parent_id
# ---------------------------------------------------------------------------

def test_account_is_credit_card_true() -> None:
    acc = xmlmap_to_model(_account_item_xml(is_credit_card="t"), Account)
    assert acc.is_credit_card is True


def test_account_is_credit_card_false() -> None:
    acc = xmlmap_to_model(_account_item_xml(is_credit_card="f"), Account)
    assert acc.is_credit_card is False


def test_account_is_credit_card_absent() -> None:
    acc = xmlmap_to_model(_account_item_xml(is_credit_card=None), Account)
    assert acc.is_credit_card is None


def test_account_parent_id_present_and_default() -> None:
    acc = xmlmap_to_model(_account_item_xml(parent_id="17900001"), Account)
    assert acc.parent_id == 17900001

    acc_root = xmlmap_to_model(_account_item_xml(parent_id=None), Account)
    assert acc_root.parent_id == -1


# ---------------------------------------------------------------------------
# api.get_accounts (mocked SOAP): mixed type=4 + type=9
# ---------------------------------------------------------------------------

def test_get_accounts_parses_account_and_folder() -> None:
    api = _mk_api_accounts()
    accounts = api.get_accounts()
    assert len(accounts) == 2
    assert all(isinstance(a, Account) for a in accounts)

    leaf, folder = accounts
    assert leaf.id == 17909584
    assert leaf.object_type is ObjectType.ACCOUNT
    assert leaf.is_credit_card is False
    assert leaf.parent_id == 17900001

    assert folder.id == 17900001
    assert folder.object_type == 9  # folder: raw int, unknown to the enum
    assert folder.name == "Банк"
    assert folder.is_credit_card is None
    assert folder.parent_id == -1


def test_get_accounts_object_types_are_int_coercible() -> None:
    """Downstream consumers store the type as int – works for enum and int alike."""
    accounts = _mk_api_accounts().get_accounts()
    assert [int(a.object_type) for a in accounts] == [4, 9]


def test_get_accounts_passes_credentials() -> None:
    api = _mk_api_accounts()
    api.get_accounts()
    args = api.client.service.getPlaceList.call_args.args
    assert args == ("k", "l", "p")


def test_get_accounts_no_id_list_skips_kwarg() -> None:
    """Without id_list, idList must be SkipValue (not sent to server)."""
    import zeep

    api = _mk_api_accounts()
    api.get_accounts()
    call_kwargs = api.client.service.getPlaceList.call_args.kwargs
    assert call_kwargs.get("idList") is zeep.xsd.SkipValue
