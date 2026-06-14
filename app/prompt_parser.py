"""Placeholder plain-English prompt parser."""


def parse_prompt(prompt: str) -> dict:
    """Parse a county GIS request into simple placeholder terms.

    TODO: Extract intent, geography, layers, filters, symbology, and outputs.
    """
    terms = [term.strip(".,!?").lower() for term in prompt.split() if term.strip()]
    return {
        "raw_prompt": prompt,
        "terms": terms,
    }

