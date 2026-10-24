# Dashboard metrics

The dashboard uses completed calls for its count and average metrics. Missing averages
are null, while empty counts are zero. Real zero measurements remain visible.
Voice quality is the stored percentage; it is not converted into an inferred NISQA MOS.
This change does not alter upstream evaluation fallbacks or add measurement provenance.

Latency shows the last ten completed calls in chronological order. Daily ingestion
counts all call statuses by their ingestion timestamp over the last seven UTC calendar
days, filling intervening days with zero. Both charts show an empty state when no
records exist for their respective query. A single latency point is supported.

## Local verification without Redis

Set `VITE_ENABLE_LIVE_UPDATES=false` in the ignored
`frontend-benten/.env.local` and restart the frontend server. This development-only
setting disables the stream and leaves manual refresh available. SSE remains enabled
by default and in production, with the existing authentication token supplied to the
stream endpoint. A Redis-backed stream is needed to verify live completion events.

Run `python -m pytest tests/test_dashboard_api.py -q` from `backend` in its virtual
environment. Tests cover empty data, real zero measurements, real aggregates,
missing quality, the seven-day window, and project isolation.

For browser checks, verify empty cards and charts, then verify populated data and a
single-point latency chart in a disposable test database. Never commit local `.env`
files or the SQLite database.
