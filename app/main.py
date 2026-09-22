import logging
import threading
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Response

from app import scheduler
from app.cache import Snapshot, cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    threading.Thread(target=cache.refresh, daemon=True).start()
    scheduler.start()
    yield
    scheduler.stop()


app = FastAPI(title="montandon-eoapi-stats", lifespan=lifespan)


def require_snapshot() -> Snapshot:
    snapshot = cache.snapshot()
    if snapshot is None:
        raise HTTPException(status_code=503, detail="stats not yet available, initial refresh still in progress")
    return snapshot


CachedSnapshot = Annotated[Snapshot, Depends(require_snapshot)]


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/readyz")
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
        "generated_at": snapshot.generated_at.isoformat(),
    }


@app.get("/stats/collections")
def collections(snapshot: CachedSnapshot):
    return snapshot.collections


@app.get("/stats/sources")
def sources(snapshot: CachedSnapshot):
    return snapshot.sources


@app.get("/stats/events-by-hazard-type")
def events_by_hazard_type(snapshot: CachedSnapshot):
    return snapshot.events_by_hazard_type


@app.get("/stats/events-by-year")
def events_by_year(snapshot: CachedSnapshot):
    return snapshot.events_by_year
