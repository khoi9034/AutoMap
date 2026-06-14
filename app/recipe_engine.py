"""Placeholder map recipe engine."""


def build_recipe(prompt: str, layer_catalog: list[dict]) -> dict:
    """Return a minimal mock recipe for a plain-English GIS request.

    TODO: Convert parsed prompts and approved layer matches into structured
    map recipes.
    """
    return {
        "request": prompt,
        "layers": layer_catalog[:1],
        "status": "placeholder",
    }

