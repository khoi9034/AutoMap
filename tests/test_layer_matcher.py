from app.layer_matcher import match_layers


def test_match_layers_returns_empty_list_without_terms():
    catalog = [{"id": "parcels", "name": "Parcels"}]

    assert match_layers([], catalog) == []


def test_match_layers_returns_placeholder_catalog_match():
    catalog = [{"id": "parcels", "name": "Parcels"}]

    assert match_layers(["parcels"], catalog) == catalog

