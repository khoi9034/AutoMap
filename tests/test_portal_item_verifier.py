import json

from app.portal_item_verifier import (
    build_verification_receipt,
    verify_item_data_layers,
    verify_item_is_private,
    verify_item_not_shared_org,
    verify_item_not_shared_public,
    verify_item_tags,
    verify_item_title_prefix,
    verify_item_type_webmap,
)


def approved_webmap():
    return {
        "operationalLayers": [
            {
                "title": "FloodPlain100year",
                "url": "https://location.example.com/arcgis/rest/services/OpenData/Flood/MapServer/2",
            }
        ]
    }


class FakeItem:
    id = "abc123"
    url = "https://example.com/items/abc123"
    title = "AutoMap Draft - Concord Flood Exposure Draft"
    type = "Web Map"
    access = "private"
    tags = ["AutoMap", "Draft", "GIS Request Engine", "Cabarrus County", "Human Review Required"]
    shared_with = {"everyone": False, "org": False, "groups": []}

    def __init__(self, *, access="private", data=None, shared_with=None):
        self.access = access
        self._data = data if data is not None else approved_webmap()
        if shared_with is not None:
            self.shared_with = shared_with

    def get_data(self):
        return self._data


def write_approved_packet(tmp_path):
    packet = tmp_path / "approved_packet"
    packet.mkdir()
    (packet / "approved_webmap.json").write_text(json.dumps(approved_webmap()), encoding="utf-8")
    return packet


def test_verifier_confirms_private_item():
    item = FakeItem()

    assert verify_item_is_private(item)["passed"] is True
    assert verify_item_not_shared_public(item)["passed"] is True
    assert verify_item_not_shared_org(item)["passed"] is True
    assert verify_item_type_webmap(item)["passed"] is True
    assert verify_item_title_prefix(item)["passed"] is True
    assert verify_item_tags(item)["passed"] is True


def test_verifier_fails_if_public_sharing_detected():
    item = FakeItem(access="public", shared_with={"everyone": True, "org": False})

    assert verify_item_is_private(item)["passed"] is False
    assert verify_item_not_shared_public(item)["passed"] is False


def test_verifier_fails_if_org_sharing_detected():
    item = FakeItem(access="org", shared_with={"everyone": False, "org": True})

    assert verify_item_not_shared_org(item)["passed"] is False


def test_verifier_checks_layer_urls():
    item = FakeItem()

    result = verify_item_data_layers(item, approved_webmap())

    assert result["passed"] is True
    assert result["missing_urls"] == []
    assert result["unexpected_urls"] == []


def test_verifier_fails_when_layer_urls_do_not_match():
    item = FakeItem(data={"operationalLayers": [{"title": "Other", "url": "https://example.com/other/MapServer/0"}]})

    result = verify_item_data_layers(item, approved_webmap())

    assert result["passed"] is False
    assert result["missing_urls"]
    assert result["unexpected_urls"]


def test_build_verification_receipt_has_no_secret_values(tmp_path):
    packet = write_approved_packet(tmp_path)

    receipt = build_verification_receipt(FakeItem(), packet)
    serialized = json.dumps(receipt).lower()

    assert receipt["verified_private"] is True
    assert receipt["verified_not_public"] is True
    assert receipt["verified_not_org_shared"] is True
    assert receipt["verified_layer_urls"] is True
    assert "password" not in serialized
    assert "token" not in serialized
    assert "cfs_dev" not in serialized
