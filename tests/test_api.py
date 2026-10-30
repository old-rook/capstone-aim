import importlib

import httpx
import pytest
import mtg_judge_ai.api.scryfall as api



# --------------------------------------------------
# MOCK DATA
# --------------------------------------------------

CARD_ID = "12345678-1234-1234-1234-123456789abc"

CARD_RESPONSE = {
    "id": CARD_ID,
    "name": "Magus of the Moon",
    "type_line": "Creature — Human Wizard",
    "mana_cost": "{2}{R}",
    "oracle_text": "Nonbasic lands are Mountains.",
}

RULINGS_RESPONSE = {
    "data": [
        {
            "source": "wotc",
            "published_at": "2018-03-16",
            "comment": "Example ruling.",
        },
        {
            "source": "gatherer",
            "published_at": "2019-01-01",
            "comment": "Another example ruling.",
        },
    ]
}


# --------------------------------------------------
# MOCK HTTP CLIENT
# --------------------------------------------------

class MockResponse:

    def __init__(self, data=None, status_code=200):
        self.data = data
        self.status_code = status_code

    def json(self):
        if isinstance(self.data, Exception):
            raise self.data

        return self.data

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("GET", "https://api.scryfall.com")
            response = httpx.Response(
                self.status_code,
                request=request,
            )
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}",
                request=request,
                response=response,
            )


class MockClient:

    def __init__(self, responses=None, error=None):
        self.responses = responses or {}
        self.error = error
        self.calls = []
        self.base_url = None
        self.headers = None
        self.timeout = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def get(self, url, params=None):
        self.calls.append({
            "url": url,
            "params": params,
        })

        if self.error:
            raise self.error

        response = self.responses.get(url)

        if response is None:
            raise AssertionError(
                f"Unexpected API request: {url}"
            )

        return response


# --------------------------------------------------
# FIXTURES
# --------------------------------------------------

@pytest.fixture(autouse=True)
def clear_caches():
    """Prevent cached values from leaking between tests."""

    api.cards_cache.clear()
    api.rulings_cache.clear()

    yield

    api.cards_cache.clear()
    api.rulings_cache.clear()


@pytest.fixture
def mock_card(monkeypatch):
    """Replace MTGCard with a predictable test implementation."""

    class FakeMTGCard:

        @staticmethod
        def from_scryfall_json(data, rulings):
            return {
                "card": data,
                "rulings": rulings,
            }

    monkeypatch.setattr(api, "MTGCard", FakeMTGCard)

    # Avoid actual sleeps during tests.
    monkeypatch.setattr(
        api,
        "_rate_limit_pause",
        lambda *args, **kwargs: None,
    )


@pytest.fixture
def mock_ruling(monkeypatch):
    """Replace CardRuling with a predictable test implementation."""

    class FakeCardRuling:

        def __init__(
            self,
            source,
            published_at,
            comment,
        ):
            self.source = source
            self.published_at = published_at
            self.comment = comment

    monkeypatch.setattr(
        api,
        "CardRuling",
        FakeCardRuling,
    )


@pytest.fixture
def client_factory(monkeypatch):
    """Inject mock HTTP clients into the API implementation."""

    clients = []

    def factory(
        base_url=None,
        headers=None,
        timeout=None,
    ):
        client = MockClient()

        client.base_url = base_url
        client.headers = headers
        client.timeout = timeout

        clients.append(client)

        return client

    monkeypatch.setattr(
        api.httpx,
        "Client",
        factory,
    )

    return clients


# --------------------------------------------------
# CARD METADATA TESTS
# --------------------------------------------------

def test_fetch_card_metadata_success(client_factory):

    client = MockClient({
        "/cards/named": MockResponse(CARD_RESPONSE)
    })

    result = api._fetch_card_metadata(
        client,
        "Magus of the Moon",
    )

    assert result == CARD_RESPONSE

    assert client.calls == [
        {
            "url": "/cards/named",
            "params": {"fuzzy": "Magus of the Moon"},
        }
    ]


def test_fetch_card_metadata_not_found(client_factory):

    client = MockClient({
        "/cards/named": MockResponse(
            {"details": "Card not found"},
            status_code=404,
        )
    })

    with pytest.raises(ValueError, match="No matching card found"):
        api._fetch_card_metadata(
            client,
            "Nonexistent Card",
        )


def test_fetch_card_metadata_server_error():

    client = MockClient({
        "/cards/named": MockResponse(
            {"error": "Internal server error"},
            status_code=500,
        )
    })

    with pytest.raises(httpx.HTTPStatusError):
        api._fetch_card_metadata(
            client,
            "Magus of the Moon",
        )


def test_fetch_card_metadata_invalid_json():

    client = MockClient({
        "/cards/named": MockResponse(
            ValueError("Invalid JSON")
        )
    })

    with pytest.raises(ValueError, match="Invalid JSON"):
        api._fetch_card_metadata(
            client,
            "Magus of the Moon",
        )


# --------------------------------------------------
# RULINGS TESTS
# --------------------------------------------------

def test_fetch_card_rulings_success(mock_ruling):

    client = MockClient({
        f"/cards/{CARD_ID}/rulings": MockResponse(
            RULINGS_RESPONSE
        )
    })

    result = api._fetch_card_ruling_by_id(
        client,
        CARD_ID,
    )

    assert len(result) == 2

    assert result[0].source == "wotc"
    assert result[0].published_at == "2018-03-16"
    assert result[0].comment == "Example ruling."

    assert result[1].source == "gatherer"


def test_fetch_card_rulings_empty_response(mock_ruling):

    client = MockClient({
        f"/cards/{CARD_ID}/rulings": MockResponse({
            "data": []
        })
    })

    result = api._fetch_card_ruling_by_id(
        client,
        CARD_ID,
    )

    assert result == []


def test_fetch_card_rulings_missing_data(mock_ruling):

    client = MockClient({
        f"/cards/{CARD_ID}/rulings": MockResponse({})
    })

    result = api._fetch_card_ruling_by_id(
        client,
        CARD_ID,
    )

    assert result == []


def test_fetch_card_rulings_default_values(mock_ruling):

    client = MockClient({
        f"/cards/{CARD_ID}/rulings": MockResponse({
            "data": [
                {}
            ]
        })
    })

    result = api._fetch_card_ruling_by_id(
        client,
        CARD_ID,
    )

    assert len(result) == 1
    assert result[0].source == "gatherer"
    assert result[0].published_at == ""
    assert result[0].comment == ""


def test_fetch_card_rulings_server_error():

    client = MockClient({
        f"/cards/{CARD_ID}/rulings": MockResponse(
            {},
            status_code=503,
        )
    })

    with pytest.raises(httpx.HTTPStatusError):
        api._fetch_card_ruling_by_id(
            client,
            CARD_ID,
        )


def test_fetch_card_rulings_invalid_json(mock_ruling):

    client = MockClient({
        f"/cards/{CARD_ID}/rulings": MockResponse(
            ValueError("Invalid JSON")
        )
    })

    with pytest.raises(ValueError):
        api._fetch_card_ruling_by_id(
            client,
            CARD_ID,
        )


# --------------------------------------------------
# CACHE TESTS
# --------------------------------------------------

def test_card_rulings_are_cached(mock_ruling):

    client = MockClient({
        f"/cards/{CARD_ID}/rulings": MockResponse(
            RULINGS_RESPONSE
        )
    })

    first_result = api._fetch_card_ruling_by_id(
        client,
        CARD_ID,
    )

    second_result = api._fetch_card_ruling_by_id(
        client,
        CARD_ID,
    )

    assert first_result is second_result

    # Only one HTTP request should have occurred.
    assert len(client.calls) == 1


def test_rulings_cache_isolated_by_card_id(mock_ruling):

    second_card_id = "another-card-id"

    client = MockClient({
        f"/cards/{CARD_ID}/rulings": MockResponse({
            "data": []
        }),
        f"/cards/{second_card_id}/rulings": MockResponse({
            "data": []
        }),
    })

    api._fetch_card_ruling_by_id(client, CARD_ID)

    api._fetch_card_ruling_by_id(
        client,
        second_card_id,
    )

    assert len(client.calls) == 2

    assert CARD_ID in api.rulings_cache
    assert second_card_id in api.rulings_cache


def test_card_cache_uses_normalized_name(
    mock_card,
    client_factory,
    monkeypatch,
):

    expected_card = {"test": "card"}

    api.cards_cache["magus of the moon"] = expected_card

    result = api.get_card_by_fuzzy_name(
        "  MAGUS OF THE MOON  "
    )

    assert result is expected_card

    # Cache hit should not create an HTTP client.
    assert client_factory == []


def test_card_cache_does_not_return_different_cards():

    first_card = {"name": "Card A"}
    second_card = {"name": "Card B"}

    api.cards_cache["card a"] = first_card
    api.cards_cache["card b"] = second_card

    assert api.cards_cache["card a"] is first_card
    assert api.cards_cache["card b"] is second_card


def test_card_cache_respects_maxsize():

    assert api.cards_cache.maxsize == 500
    assert api.rulings_cache.maxsize == 500


def test_cache_has_one_hour_ttl():

    assert api.cards_cache.ttl == 3600
    assert api.rulings_cache.ttl == 3600


# --------------------------------------------------
# MAIN FUNCTION INTEGRATION TESTS
# --------------------------------------------------

def test_get_card_by_fuzzy_name_success(
    mock_card,
    mock_ruling,
    client_factory,
    monkeypatch,
):
    # Configure the mock client before the API call.
    def factory(**kwargs):
        mock = MockClient({
            "/cards/named": MockResponse(CARD_RESPONSE),
            f"/cards/{CARD_ID}/rulings": MockResponse(
                RULINGS_RESPONSE
            ),
        })

        mock.base_url = kwargs.get("base_url")
        mock.headers = kwargs.get("headers")
        mock.timeout = kwargs.get("timeout")

        client_factory.append(mock)

        return mock

    monkeypatch.setattr(api.httpx, "Client", factory)

    result = api.get_card_by_fuzzy_name(
        "Magus of the Moon"
    )

    assert result["card"] == CARD_RESPONSE
    assert len(result["rulings"]) == 2

    assert (
        api.cards_cache["magus of the moon"]
        is result
    )

    assert len(client_factory) == 1


def test_get_card_by_fuzzy_name_uses_card_cache(
    mock_card,
    client_factory,
):

    expected_card = {"cached": True}

    api.cards_cache["magus of the moon"] = expected_card

    result = api.get_card_by_fuzzy_name(
        "Magus of the Moon"
    )

    assert result is expected_card
    assert len(client_factory) == 0


def test_failed_card_lookup_does_not_cache_result(
    mock_card,
    client_factory,
    monkeypatch,
):

    def factory(**kwargs):
        return MockClient({
            "/cards/named": MockResponse(
                {},
                status_code=404,
            )
        })

    monkeypatch.setattr(api.httpx, "Client", factory)

    with pytest.raises(ValueError):
        api.get_card_by_fuzzy_name(
            "Nonexistent Card"
        )

    assert "nonexistent card" not in api.cards_cache


# --------------------------------------------------
# HTTP CLIENT CONFIGURATION TESTS
# --------------------------------------------------

def test_http_client_configuration(
    mock_card,
    mock_ruling,
    monkeypatch,
):

    captured = {}

    def factory(**kwargs):
        captured.update(kwargs)

        return MockClient({
            "/cards/named": MockResponse(CARD_RESPONSE),
            f"/cards/{CARD_ID}/rulings": MockResponse({
                "data": []
            }),
        })

    monkeypatch.setattr(
        api.httpx,
        "Client",
        factory,
    )

    api.get_card_by_fuzzy_name("Magus of the Moon")

    assert captured["base_url"] == api.SCRYFALL_BASE_URL
    assert captured["headers"] == api.HEADERS
    assert captured["timeout"] == 10.0


# --------------------------------------------------
# RATE LIMIT TESTS
# --------------------------------------------------

def test_rate_limit_does_not_sleep_when_interval_elapsed(
    monkeypatch,
):

    timestamps = iter([100.0, 100.0])

    monkeypatch.setattr(
        api.time,
        "time",
        lambda: next(timestamps),
    )

    def unexpected_sleep(_):
        pytest.fail("Unexpected sleep occurred")

    monkeypatch.setattr(
        api.time,
        "sleep",
        unexpected_sleep,
    )

    monkeypatch.setattr(
        api,
        "_last_request_time",
        0.0,
    )

    api._rate_limit_pause(min_interval=0.1)

    assert api._last_request_time == 100.0


def test_rate_limit_sleeps_when_requests_are_too_close(
    monkeypatch,
):

    timestamps = iter([100.05, 100.15])
    sleep_calls = []

    monkeypatch.setattr(
        api.time,
        "time",
        lambda: next(timestamps),
    )

    monkeypatch.setattr(
        api.time,
        "sleep",
        lambda duration: sleep_calls.append(duration),
    )

    monkeypatch.setattr(
        api,
        "_last_request_time",
        100.0,
    )

    api._rate_limit_pause(min_interval=0.1)

    assert len(sleep_calls) == 1
    assert sleep_calls[0] == pytest.approx(0.05)

    assert api._last_request_time == 100.15


# --------------------------------------------------
# SECURITY TESTS
# --------------------------------------------------

def test_no_api_key_is_required_or_sent(
    mock_card,
    mock_ruling,
    client_factory,
    monkeypatch,
):

    def factory(**kwargs):
        client = MockClient({
            "/cards/named": MockResponse(CARD_RESPONSE),
            f"/cards/{CARD_ID}/rulings": MockResponse({
                "data": []
            }),
        })

        client.headers = kwargs.get("headers")
        client.base_url = kwargs.get("base_url")
        client.timeout = kwargs.get("timeout")

        client_factory.append(client)

        return client

    monkeypatch.setattr(api.httpx, "Client", factory)

    api.get_card_by_fuzzy_name("Magus of the Moon")

    headers = client_factory[0].headers

    assert "Authorization" not in headers
    assert "api_key" not in headers
    assert "API-Key" not in headers


def test_404_error_does_not_expose_sensitive_information():

    client = MockClient({
        "/cards/named": MockResponse(
            {},
            status_code=404,
        )
    })

    with pytest.raises(ValueError) as exc_info:
        api._fetch_card_metadata(
            client,
            "Nonexistent Card",
        )

    error_message = str(exc_info.value)

    assert "No matching card found" in error_message

    # Ensure no authorization or credential information appears.
    assert "Bearer " not in error_message
    assert "api_key" not in error_message.lower()
    assert "password" not in error_message.lower()
