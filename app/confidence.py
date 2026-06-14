"""Placeholder confidence scoring helpers."""


def score_confidence(matches: list[dict]) -> float:
    """Return a simple placeholder confidence score.

    TODO: Replace with explainable scoring based on prompt fit, layer quality,
    and ambiguity.
    """
    return 0.0 if not matches else 0.5

