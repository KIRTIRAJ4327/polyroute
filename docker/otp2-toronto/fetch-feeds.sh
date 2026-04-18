#!/usr/bin/env bash
# Fetch GTFS feeds and OSM extract for the GTA, then drop them in
# ./graph-data/ where OTP2 will pick them up on graph build.
#
# URLs may drift. If one fails, check the agency open-data page and
# update below. Last verified: April 2026.

set -euo pipefail

DATA_DIR="$(dirname "$0")/graph-data"
mkdir -p "$DATA_DIR"
cd "$DATA_DIR"

echo "==> Fetching OSM extract for Ontario (~350 MB)..."
curl -L -o ontario.osm.pbf \
  "https://download.geofabrik.de/north-america/canada/ontario-latest.osm.pbf"

echo "==> Fetching TTC GTFS..."
curl -L -o ttc.gtfs.zip \
  "https://opendata.toronto.ca/TTC/routings/OpenData_TTC_Schedules.zip" \
  || echo "  (TTC URL drift — check https://www.ttc.ca/open-data)"

echo "==> Fetching GO Transit + UP Express GTFS..."
curl -L -o go.gtfs.zip \
  "https://www.gotransit.com/static_files/gotransit/assets/Files/GO_GTFS.zip"

echo "==> Fetching MiWay GTFS..."
curl -L -o miway.gtfs.zip \
  "https://www.miapp.ca/GTFS/google_transit.zip"

echo "==> Fetching Brampton Transit GTFS..."
curl -L -o brampton.gtfs.zip \
  "https://www.brampton.ca/EN/City-Hall/OpenGov/Open-Data-Catalogue/OpenDataFiles/google_transit.zip" \
  || echo "  (Brampton URL drift — check open-data catalogue)"

echo ""
echo "==> Done. Contents of $DATA_DIR:"
ls -lh "$DATA_DIR"

cat <<'EOF'

Next step:
  docker compose up

First boot builds the graph (3–8 minutes). OTP2 will be at
  http://localhost:8080

EOF
