"""
llm_extract.py — optional LLM-powered happy-hour menu extraction (pass 2).

The heuristic parser in pass2_extract.py handles clean menus, but real menus
vary wildly in layout — name-above-price (Wilder), price-above-items under a
section header (Bellini "BEER / $5 / Miller Lite"), inline prices, custom
cocktail names with no recognizable type word. An LLM reads all of these
correctly in one pass and also pulls the happy-hour time window.

Used by `pass2_extract.py --llm`. The LLM call goes through `llm_client.py`,
which defaults to a **local Ollama model — free, private, no Anthropic tokens**.
Switch backends with the `LLM_PROVIDER` env var (ollama | openai | anthropic).
Falls back to the heuristic parser when no backend is reachable.
"""

import json

# Structured-output schema — the backend guarantees the response matches this.
SCHEMA = {
    'type': 'object',
    'additionalProperties': False,
    'properties': {
        'happy_hour_times': {
            'type': 'string',
            'description': "The happy hour day/time window exactly as written, e.g. "
                           "'Mon-Fri 4-6pm' or 'Every day 4:30-6:30pm'. Empty string if not stated.",
        },
        'items': {
            'type': 'array',
            'items': {
                'type': 'object',
                'additionalProperties': False,
                'properties': {
                    'name': {'type': 'string', 'description': 'The item name as printed on the menu.'},
                    'normalized_item': {
                        'type': 'string',
                        'description': "The drink TYPE. e.g. 'Sam Adams Lager'->'Lager', "
                                       "'Lime Margarita'->'Margarita', 'House Cabernet'->'Cabernet Sauvignon', "
                                       "'Kenwood Light Lager'->'Lager'. For food, a short dish category.",
                    },
                    'category': {
                        'type': 'string',
                        'enum': ['beer', 'wine', 'cocktail', 'seltzer', 'cider', 'spirit', 'food', 'other'],
                    },
                    'price': {'type': 'number', 'description': 'Happy-hour price in dollars.'},
                },
                'required': ['name', 'normalized_item', 'category', 'price'],
            },
        },
    },
    'required': ['happy_hour_times', 'items'],
}

SYSTEM = (
    "You extract structured happy-hour menu data from raw scraped text. Be precise and "
    "only include drink/food items that are part of the HAPPY HOUR offering with a happy-hour "
    "price. Ignore regular/full-menu sections, descriptions, and non-priced lines."
)

PROMPT = (
    "From the happy-hour menu text below, extract every happy-hour item with its price.\n"
    "Rules:\n"
    "- normalized_item is the drink TYPE, not the brand: 'Sam Adams Lager'->'Lager', "
    "'Lime Margarita'->'Margarita', 'Pinot Grigio (Cielo)'->'Pinot Grigio', 'House Cabernet'->'Cabernet Sauvignon'.\n"
    "- Menus list prices in different layouts. Sometimes the price is a section header that applies to the items "
    "under it (e.g. 'BEER' then '$5' then 'Miller Lite' means Miller Lite is $5). Sometimes the price is at the end "
    "of the item's line or its description. Handle all of these.\n"
    "- A drink's name may span multiple lines (e.g. 'KENWOOD LIGHT' then 'LAGER' = 'Kenwood Light Lager').\n"
    "- Skip ingredient/description lines, ABV, city/region, and section headers themselves.\n"
    "- Also extract the happy-hour day/time window if the text states one.\n\n"
    "MENU TEXT:\n"
)


def available():
    """True if the configured backend (default: local Ollama) is reachable."""
    try:
        import llm_client
        llm_client.preflight()
        return True
    except Exception:
        return False


def extract_with_llm(menu_text, bar_name=''):
    """Return {'happy_hour_times': str, 'items': [{name, normalized_item, category, price}]}.
    Raises on hard backend/parse failure so the caller can fall back to heuristics."""
    from llm_client import complete_json
    data = complete_json(SYSTEM, PROMPT + (menu_text or '')[:18000], SCHEMA, max_tokens=4096)
    data.setdefault('items', [])
    data.setdefault('happy_hour_times', '')
    return data
