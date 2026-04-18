# OpenTripPlanner 2 — Toronto / GTA

Runs a local OTP2 instance covering:
- **TTC** — subway, streetcar, bus
- **GO Transit** — regional rail + bus
- **UP Express** — Union ↔ Pearson
- **MiWay** — Mississauga
- **Brampton Transit**
- **Bike Share Toronto** (GBFS, live)

## One-time setup

Run the fetch script to pull GTFS feeds and the OSM extract for the GTA:

```bash
cd docker/otp2-toronto
./fetch-feeds.sh
```

This downloads ~400 MB to `./graph-data/`. Feeds are refreshed each time you
run the script; OTP2 rebuilds the graph on startup.

## Start OTP2

```bash
docker compose up
```

First boot takes 3–8 minutes (graph build). Subsequent boots are ~30 seconds.

Once ready, the GraphQL endpoint is at:

```
http://localhost:8080/otp/routers/default/index/graphql
```

And the web UI at:

```
http://localhost:8080
```

## Memory

OTP2 will want 4–8 GB for the full GTA graph. If you see OOM kills, bump
`JAVA_OPTS` in `docker-compose.yml` or drop Brampton/Oakville to shrink scope.

## Feed sources

| Agency | URL | License |
|---|---|---|
| TTC | https://www.ttc.ca/open-data | Open |
| GO Transit | https://www.gotransit.com/static_files/gotransit/assets/Files/GO_GTFS.zip | Open |
| UP Express | bundled in GO feed | Open |
| MiWay | https://www.miapp.ca/GTFS/google_transit.zip | Open |
| Brampton Transit | https://www.brampton.ca/EN/City-Hall/OpenGov/Open-Data-Catalogue/Pages/Google-Transit-Feed-Specification.aspx | Open |
| OSM extract (Ontario) | https://download.geofabrik.de/north-america/canada/ontario.html | ODbL |

GTFS URLs drift — if fetch fails, check the agency open-data page. Canada's
Open Government portal (https://open.canada.ca) mirrors most feeds.
