import json

from app.address_normalizer import parse_address
from app.address_parcel_resolver import resolve_verified_address


def point_feature(address="793 BARTRAM AVE", object_id=1):
    return {
        "type": "Feature",
        "properties": {"OBJECTID": object_id, "FULLADDR": address, "CITY": "CONCORD", "ZIP": "28025", "PIN14": "12345678901234"},
        "geometry": {"type": "Point", "coordinates": [-80.58, 35.36]},
    }


class ProgressiveAddressClient:
    def __init__(self, counts, features=None):
        self.counts = list(counts)
        self.features = features or [point_feature()]
        self.count_queries = []
        self.feature_queries = []

    def query_count(self, layer_url, *, where=None, **kwargs):
        self.count_queries.append({"layer_url": layer_url, "where": where, "return_geometry": False, **kwargs})
        count = self.counts.pop(0) if self.counts else 0
        return {"count": count, "return_geometry": False}

    def query_features(self, layer_url, *, where=None, out_fields="*", return_geometry=True, result_record_count=None, **kwargs):
        self.feature_queries.append(
            {
                "layer_url": layer_url,
                "where": where,
                "out_fields": out_fields,
                "return_geometry": return_geometry,
                "result_record_count": result_record_count,
                **kwargs,
            }
        )
        return {"status": "ok", "features": self.features[: result_record_count or len(self.features)]}


def address_field_map(split=False):
    fields = {
        "object_id": ["OBJECTID"],
        "full_address": ["FULLADDR"],
        "city": ["CITY"],
        "zip": ["ZIP"],
        "pin14": ["PIN14"],
        "pin": [],
        "parcel_id": [],
    }
    if split:
        fields.update({"house_number": ["ADDRNUM"], "street_name": ["STNAME"], "street_suffix": ["STTYPE"]})
    return {
        "layer_key": "addresses",
        "layer_name": "Addresses",
        "layer_url": "https://example.test/Addresses/0",
        "fields_by_role": fields,
        "warnings": [],
    }


def test_address_normalizer_generates_ave_and_avenue_variants():
    parsed = parse_address("793 bartram ave")

    assert parsed["house_number"] == "793"
    assert parsed["street_name_core"] == "bartram"
    assert parsed["suffix"] == "ave"
    assert parsed["address_like"] is True
    assert "793 bartram ave" in parsed["normalized_variants"]
    assert "793 bartram avenue" in parsed["normalized_variants"]


def test_address_matcher_tries_house_number_and_street_core(monkeypatch):
    monkeypatch.setattr("app.address_parcel_resolver.build_verified_address_field_map", lambda schema_name="automap": address_field_map(split=True))
    monkeypatch.setattr(
        "app.address_parcel_resolver.find_tax_parcel_layer",
        lambda layer_catalog=None, schema_name="automap": None,
    )
    client = ProgressiveAddressClient(counts=[0, 1], features=[point_feature()])

    result = resolve_verified_address("793 bartram ave", client=client)

    attempts = [attempt["attempt"] for attempt in result["query_attempts"]]
    assert attempts[:2] == ["exact_normalized_full_address", "house_number_street_core"]
    assert result["match_status"] == "matched"
    assert client.count_queries[0]["return_geometry"] is False
    assert client.feature_queries[-1]["return_geometry"] is True


def test_address_matcher_returns_candidates_instead_of_immediate_unmatched(monkeypatch):
    monkeypatch.setattr("app.address_parcel_resolver.build_verified_address_field_map", lambda schema_name="automap": address_field_map())
    monkeypatch.setattr(
        "app.address_parcel_resolver.find_tax_parcel_layer",
        lambda layer_catalog=None, schema_name="automap": None,
    )
    client = ProgressiveAddressClient(
        counts=[0, 0, 2],
        features=[point_feature("793 BARTRAM AVE SW", 1), point_feature("793 BARTRAM AVE NE", 2)],
    )

    result = resolve_verified_address("793 bartram ave", client=client)

    assert result["match_status"] == "ambiguous"
    assert len(result["candidate_matches"]) == 2
    assert result["candidate_matches"][0]["display_address"] == "793 BARTRAM AVE SW"
    assert client.feature_queries[-1]["return_geometry"] is False


def test_exact_address_match_returns_matched(monkeypatch):
    monkeypatch.setattr("app.address_parcel_resolver.build_verified_address_field_map", lambda schema_name="automap": address_field_map())
    monkeypatch.setattr(
        "app.address_parcel_resolver.find_tax_parcel_layer",
        lambda layer_catalog=None, schema_name="automap": None,
    )
    client = ProgressiveAddressClient(counts=[1], features=[point_feature("793 BARTRAM AVE")])

    result = resolve_verified_address("793 Bartram Avenue", client=client)

    assert result["match_status"] == "matched"
    assert result["related_pin14"] == "12345678901234"
    assert result["downloaded_geometry"] is True


def test_multiple_mock_matches_return_ambiguous(monkeypatch):
    monkeypatch.setattr("app.address_parcel_resolver.build_verified_address_field_map", lambda schema_name="automap": address_field_map())
    monkeypatch.setattr(
        "app.address_parcel_resolver.find_tax_parcel_layer",
        lambda layer_catalog=None, schema_name="automap": None,
    )
    client = ProgressiveAddressClient(
        counts=[2],
        features=[point_feature("793 BARTRAM AVE", 1), point_feature("793 BARTRAM AVE UNIT B", 2)],
    )

    result = resolve_verified_address("793 bartram ave", client=client)

    assert result["match_status"] == "ambiguous"
    assert len(result["candidate_matches"]) == 2


def test_address_matching_does_not_search_owner_or_bulk_download(monkeypatch):
    monkeypatch.setattr("app.address_parcel_resolver.build_verified_address_field_map", lambda schema_name="automap": address_field_map())
    monkeypatch.setattr(
        "app.address_parcel_resolver.find_tax_parcel_layer",
        lambda layer_catalog=None, schema_name="automap": None,
    )
    client = ProgressiveAddressClient(counts=[0, 0, 0, 0])

    result = resolve_verified_address("793 bartram ave owner smith", client=client)
    serialized = json.dumps({"queries": client.count_queries + client.feature_queries}).lower()

    assert result["match_status"] == "unmatched"
    assert "owner smith" not in serialized
    assert "ownername" not in serialized
    assert "owner_name" not in serialized
    assert len(client.feature_queries) == 0


def test_out_of_scope_address_returns_unsupported_area_without_query(monkeypatch):
    monkeypatch.setattr("app.address_parcel_resolver.build_verified_address_field_map", lambda schema_name="automap": address_field_map())
    monkeypatch.setattr(
        "app.address_parcel_resolver.find_tax_parcel_layer",
        lambda layer_catalog=None, schema_name="automap": None,
    )
    client = ProgressiveAddressClient(counts=[1], features=[point_feature("123 MAIN ST")])

    result = resolve_verified_address("123 Main St, Charlotte NC", client=client)

    assert result["match_status"] == "unsupported_area"
    assert result["supported_area"] == "Cabarrus County, NC"
    assert "Cabarrus County records" in " ".join(result["warnings"])
    assert client.count_queries == []
    assert client.feature_queries == []
