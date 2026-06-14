from app.recipe_engine import build_recipe


def test_build_recipe_returns_placeholder_recipe():
    catalog = [{"id": "parcels", "name": "Parcels"}]

    result = build_recipe("Show parcels.", catalog)

    assert result == {
        "request": "Show parcels.",
        "layers": catalog,
        "status": "placeholder",
    }

