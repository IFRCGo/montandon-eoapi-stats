import logging
import threading
import tomllib
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Response

from app import scheduler
from app.cache import Snapshot, cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _get_version() -> str:
    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    with pyproject.open("rb") as f:
        return tomllib.load(f)["project"]["version"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    threading.Thread(target=cache.refresh, daemon=True).start()
    scheduler.start()
    yield
    scheduler.stop()


# Docs live under /stats so the whole public surface sits behind one path prefix, which lets
# the service share a hostname with another app rather than needing its own.
app = FastAPI(
    title="montandon-eoapi-stats",
    version=_get_version(),
    lifespan=lifespan,
    docs_url="/stats/docs",
    redoc_url="/stats/redoc",
    openapi_url="/stats/openapi.json",
)


def require_snapshot() -> Snapshot:
    snapshot = cache.snapshot()
    if snapshot is None:
        raise HTTPException(status_code=503, detail="stats not yet available, initial refresh still in progress")
    return snapshot


CachedSnapshot = Annotated[Snapshot, Depends(require_snapshot)]


@app.get("/stats/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/stats/readyz")
def readyz(response: Response):
    if not cache.ready:
        response.status_code = 503
        return {"status": "not ready"}
    return {"status": "ready"}


@app.get("/stats")
def stats(snapshot: CachedSnapshot):
    return {
        "total_collections": snapshot.total_collections,
        "total_events": snapshot.total_events,
        "total_hazard_items": snapshot.total_hazard_items,
        "total_impact_items": snapshot.total_impact_items,
        "total_response_items": snapshot.total_response_items,
        "generated_at": snapshot.generated_at.isoformat(),
    }


@app.get("/stats/sources")
def sources(snapshot: CachedSnapshot):
    return snapshot.sources


@app.get("/stats/events/by-hazard-type")
def events_by_hazard_type(snapshot: CachedSnapshot):
    return snapshot.events_by_hazard_type


@app.get("/stats/events/by-country")
def events_by_country(snapshot: CachedSnapshot):
    return snapshot.events_by_country


@app.get("/stats/items/by-year")
def items_by_year(snapshot: CachedSnapshot):
    return snapshot.items_by_year
