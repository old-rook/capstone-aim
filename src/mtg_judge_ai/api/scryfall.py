import time

import httpx
from cachetools import TTLCache

from mtg_judge_ai.core.schemas import CardRuling, MTGCard


SCRYFALL_BASE_URL = "https://api.scryfall.com/"
HEADERS = {
    "User-Agent": "MTGJudgeMVP/1.0",
    "Accept": "application/json;q=0.9,*/*;q=0.8",
}

cards_cache = TTLCache(maxsize=500, ttl=3600)
rulings_cache = TTLCache(maxsize=500, ttl=3600)

_last_request_time = 0.0


def _rate_limit_pause(min_interval: float = 0.1):
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < min_interval:
        time.sleep(min_interval - elapsed)
    _last_request_time = time.time()

def _fetch_card_metadata(client: httpx.Client, card_name:str) -> dict:
    _rate_limit_pause()
    card_resp = client.get("/cards/named", params={"fuzzy": card_name})
    if card_resp.status_code == 404:
        raise ValueError(f"No matching card found for `{card_name}`. Please refine your search criteria and try again.")
    card_resp.raise_for_status()
    card_json = card_resp.json()

    return card_json

def _fetch_card_ruling_by_id(client: httpx.Client, card_id: str) -> list[CardRuling]:
    rulings = rulings_cache.get(card_id)

    if rulings is None:
        _rate_limit_pause()
        rulings_resp = client.get(f"/cards/{card_id}/rulings")
        rulings_resp.raise_for_status()
        rulings_json = rulings_resp.json().get("data", [])

        rulings = [
            CardRuling(
                source=r.get("source", "gatherer"),
                published_at=r.get("published_at", ""),
                comment=r.get("comment", ""),
            )
            for r in rulings_json
        ]
        rulings_cache[card_id] = rulings
    return rulings

def get_card_by_fuzzy_name(card_name: str) -> MTGCard:
    """
    Retrieve card details and rulins from scryfall api
    Args:
        card_name: (str) Card name you want to search. This can be a single word or group of words.

    Returns:
        card_details: (str) JSON for card details.
    """
    cache_key = card_name.strip().lower()
    if cache_key in cards_cache:
        return cards_cache[cache_key]

    with httpx.Client(base_url=SCRYFALL_BASE_URL, headers=HEADERS, timeout=10.0) as scryfall:
        card_json = _fetch_card_metadata(scryfall, card_name)
        card_id = card_json.get("id")
        rulings = _fetch_card_ruling_by_id(scryfall, card_id)

    card = MTGCard.from_scryfall_json(data=card_json, rulings=rulings)
    cards_cache[cache_key] = card

    return card
