import logging
import re
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime

import psycopg
from psycopg.rows import dict_row

from app import queries
from app.config import settings

logger = logging.getLogger(__name__)

ITEM_TYPES = ("events", "hazards", "impacts", "response")
COLLECTION_SUFFIX = re.compile(r"-(events|hazards|impacts|response)$")


@dataclass
class Snapshot:
    total_collections: int
    total_events: int
    total_hazard_items: int
    total_impact_items: int
    total_response_items: int
    sources: list[dict]
    events_by_hazard_type: list[dict]
    events_by_year: list[dict]
    generated_at: datetime


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _with_iso_dates(rows: list[dict]) -> list[dict]:
    return [{**row, "earliest": _iso(row["earliest"]), "latest": _iso(row["latest"])} for row in rows]


def _split_collection(collection: str) -> tuple[str, str]:
    match = COLLECTION_SUFFIX.search(collection)
    if match is None:
        return collection, ""
    return collection[: match.start()], match.group(1)


def _merge_collections(collection_ids: list[str], stats_rows: list[dict]) -> list[dict]:
    """Every registered collection, including empty ones, annotated with source and type."""
    by_id = {row["collection"]: row for row in stats_rows}
    for collection_id in collection_ids:
        by_id.setdefault(collection_id, {"collection": collection_id, "item_count": 0, "earliest": None, "latest": None})
    merged = []
    for row in sorted(by_id.values(), key=lambda row: row["collection"]):
        source, item_type = _split_collection(row["collection"])
        merged.append({**row, "source": source, "type": item_type})
    return merged


def _aggregate_sources(collections: list[dict]) -> list[dict]:
    sources: dict[str, dict] = {}
    for row in collections:
        source = sources.setdefault(
            row["source"],
            {
                "source": row["source"],
                "events": 0,
                "hazards": 0,
                "impacts": 0,
                "response": 0,
                "total_items": 0,
                "earliest": None,
                "latest": None,
            },
        )
        if row["type"]:
            source[row["type"]] += row["item_count"]
        source["total_items"] += row["item_count"]
        if row["earliest"] and (source["earliest"] is None or row["earliest"] < source["earliest"]):
            source["earliest"] = row["earliest"]
        if row["latest"] and (source["latest"] is None or row["latest"] > source["latest"]):
            source["latest"] = row["latest"]
    return sorted(sources.values(), key=lambda source: source["source"])


@dataclass
class StatsCache:
    _snapshot: Snapshot | None = field(default=None, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)

    @property
    def ready(self) -> bool:
        return self._snapshot is not None

    def snapshot(self) -> Snapshot | None:
        with self._lock:
            return self._snapshot

    def refresh(self) -> None:
        logger.info("Refreshing stats cache from the database")
        conn_str = (
            f"host={settings.db_host} port={settings.db_port} "
            f"user={settings.db_user} password={settings.db_password} "
            f"dbname={settings.db_name}"
        )
        with psycopg.connect(conn_str, row_factory=dict_row) as conn, conn.cursor() as cur:
            # settings.query_statement_timeout is validated against STATEMENT_TIMEOUT_RE at startup.
            cur.execute(f"SET statement_timeout = '{settings.query_statement_timeout}'")

            cur.execute(queries.ALL_COLLECTIONS)
            collection_ids = [row["id"] for row in cur.fetchall()]

            cur.execute(queries.COLLECTION_STATS)
            collection_rows = cur.fetchall()

            cur.execute(queries.EVENTS_BY_HAZARD_TYPE)
            events_by_hazard_type = cur.fetchall()

            cur.execute(queries.EVENTS_BY_YEAR)
            events_by_year = cur.fetchall()

        collections = _merge_collections(collection_ids, collection_rows)
        sources = _aggregate_sources(collections)
        totals = {
            item_type: sum(row["item_count"] for row in collections if row["type"] == item_type) for item_type in ITEM_TYPES
        }

        snapshot = Snapshot(
            total_collections=len(collections),
            total_events=totals["events"],
            total_hazard_items=totals["hazards"],
            total_impact_items=totals["impacts"],
            total_response_items=totals["response"],
            sources=_with_iso_dates(sources),
            events_by_hazard_type=events_by_hazard_type,
            events_by_year=events_by_year,
            generated_at=datetime.now(UTC),
        )
        with self._lock:
            self._snapshot = snapshot
        logger.info(
            "Stats cache refreshed: %s collections, %s events, %s hazard items, %s impact items, %s response items",
            snapshot.total_collections,
            snapshot.total_events,
            snapshot.total_hazard_items,
            snapshot.total_impact_items,
            snapshot.total_response_items,
        )


cache = StatsCache()
