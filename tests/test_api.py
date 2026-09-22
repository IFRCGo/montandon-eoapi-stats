from datetime import UTC, datetime
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.cache import Snapshot, _aggregate_sources, _split_collection
from app.main import app


def make_snapshot() -> Snapshot:
    return Snapshot(
        total_collections=27,
        total_events=5162915,
        total_hazard_items=5268015,
        total_impact_items=11052102,
        collections=[
            {
                "collection": "usgs-events",
                "source": "usgs",
                "type": "events",
                "item_count": 3940515,
                "earliest": "1990-01-01T00:22:33.990000+00:00",
                "latest": "2026-09-14T23:49:53.658000+00:00",
            }
        ],
        sources=[
            {
                "source": "usgs",
                "events": 3940515,
                "hazards": 3940515,
                "impacts": 13898,
                "total_items": 7894928,
                "earliest": "1990-01-01T00:22:33.990000+00:00",
                "latest": "2026-09-14T23:49:53.658000+00:00",
            }
        ],
        events_by_hazard_type=[{"hazard_code": "EQ", "event_count": 4051947}],
        events_by_year=[{"year": 2026, "event_count": 372935}],
        generated_at=datetime.now(UTC),
    )


def test_healthz_always_ok():
    with patch("app.cache.cache.refresh", lambda: None), TestClient(app) as client:
        assert client.get("/healthz").status_code == 200


def test_stats_not_ready_before_first_refresh():
    with patch("app.cache.cache.refresh", lambda: None), TestClient(app) as client:
        assert client.get("/readyz").status_code == 503
        for path in (
            "/stats",
            "/stats/collections",
            "/stats/sources",
            "/stats/events-by-hazard-type",
            "/stats/events-by-year",
        ):
            assert client.get(path).status_code == 503


def test_stats_served_from_cache_once_ready():
    with (
        patch("app.cache.cache.refresh", lambda: None),
        patch("app.cache.cache._snapshot", make_snapshot()),
        TestClient(app) as client,
    ):
        assert client.get("/readyz").status_code == 200

        stats = client.get("/stats").json()
        assert stats["total_collections"] == 27
        assert stats["total_events"] == 5162915
        assert stats["total_hazard_items"] == 5268015
        assert stats["total_impact_items"] == 11052102

        collections = client.get("/stats/collections").json()
        assert collections[0]["collection"] == "usgs-events"
        assert collections[0]["source"] == "usgs"
        assert collections[0]["type"] == "events"

        sources = client.get("/stats/sources").json()
        assert sources[0]["source"] == "usgs"
        assert sources[0]["earliest"] == "1990-01-01T00:22:33.990000+00:00"

        assert client.get("/stats/events-by-hazard-type").json() == [{"hazard_code": "EQ", "event_count": 4051947}]
        assert client.get("/stats/events-by-year").json() == [{"year": 2026, "event_count": 372935}]


def test_split_collection_strips_only_known_suffixes():
    assert _split_collection("usgs-events") == ("usgs", "events")
    assert _split_collection("idmc-gidd-events") == ("idmc-gidd", "events")
    assert _split_collection("pdc-impacts") == ("pdc", "impacts")
    assert _split_collection("ibtracs-hazards") == ("ibtracs", "hazards")
    # A collection that doesn't follow the convention keeps its full id as the source.
    assert _split_collection("something-else") == ("something-else", "")


def test_aggregate_sources_spans_all_collections_of_a_source():
    def row(collection, source, item_type, count, earliest, latest):
        return {
            "collection": collection,
            "source": source,
            "type": item_type,
            "item_count": count,
            "earliest": datetime.fromisoformat(earliest),
            "latest": datetime.fromisoformat(latest),
        }

    sources = _aggregate_sources(
        [
            row("gdacs-events", "gdacs", "events", 130303, "1988-03-08+00:00", "2026-09-21+00:00"),
            row("gdacs-hazards", "gdacs", "hazards", 130303, "1988-03-08+00:00", "2026-09-21+00:00"),
            row("gdacs-impacts", "gdacs", "impacts", 315952, "1900-01-01+00:00", "2026-09-26+00:00"),
        ]
    )

    assert len(sources) == 1
    gdacs = sources[0]
    assert gdacs["events"] == 130303
    assert gdacs["hazards"] == 130303
    assert gdacs["impacts"] == 315952
    assert gdacs["total_items"] == 576558
    # Range spans every collection of the source, unfiltered.
    assert gdacs["earliest"] == datetime.fromisoformat("1900-01-01+00:00")
    assert gdacs["latest"] == datetime.fromisoformat("2026-09-26+00:00")
