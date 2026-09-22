# montandon-eoapi-stats

Nightly-cached stats API over the [Montandon](https://github.com/IFRCGo) eoAPI pgSTAC database.

A cron job (default: daily at 02:00) queries `pgstac` for collection, event, hazard,
impact and response counts and caches the result in memory. All API requests are served
from that cache, so the database is only ever hit once per refresh.

## Endpoints

| Path | Description |
| --- | --- |
| `GET /stats/healthz` | Liveness check |
| `GET /stats/readyz` | Readiness check (503 until the first cache refresh completes) |
| `GET /stats` | Total collections, events, hazard items, impact items, response items |
| `GET /stats/sources` | Per-source item counts and date ranges, aggregated across collections |
| `GET /stats/events/by-hazard-type` | Event counts grouped by hazard code |
| `GET /stats/events/by-year` | Event counts grouped by year |

## Configuration

Set via environment variables:

| Variable | Required | Default |
| --- | --- | --- |
| `DB_HOST` | yes | — |
| `DB_PORT` | no | `5432` |
| `DB_USER` | yes | — |
| `DB_PASSWORD` | yes | — |
| `DB_NAME` | yes | — |
| `CRON_SCHEDULE` | no | `0 2 * * *` |
| `QUERY_STATEMENT_TIMEOUT` | no | `10min` |

## Development

```sh
uv sync --all-extras
uv run pre-commit install   # run lint/format/tests on every commit
uv run uvicorn app.main:app --reload
```

Run checks manually:

```sh
uv run pre-commit run --all-files
```

## Docker

```sh
docker build -t montandon-eoapi-stats .
```

## Deployment

A Helm chart is published to `oci://ghcr.io/ifrcgo/montandon-eoapi-stats` on release (see
[`helm/`](./helm)). It expects an existing Kubernetes Secret with `DB_HOST`, `DB_PORT`,
`DB_USER`, `DB_PASSWORD`, `DB_NAME` keys, named by `existingDbSecret` in
[`helm/values.yaml`](./helm/values.yaml).

## Releases

Releases are managed by [release-please](https://github.com/googleapis/release-please)
from [Conventional Commits](https://www.conventionalcommits.org/) on `main`. Merging a
release PR tags a GitHub release, which triggers the Docker image and Helm chart publish.
