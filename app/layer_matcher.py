"""Placeholder layer matching utilities."""


def match_layers(prompt_terms: list[str], layer_catalog: list[dict]) -> list[dict]:
    """Return mock layer matches from the approved local catalog.

    TODO: Add semantic matching and confidence scoring for catalog layers.
    """
    if not prompt_terms:
        return []

    return layer_catalog[:1]

