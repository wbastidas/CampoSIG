#!/usr/bin/env bash
# Build the offline basemap and asset tiles for one zone (RF-360).
#
# Runs outside the API on purpose: tiling is minutes of CPU on a large extract, and an HTTP
# request that takes four minutes is a request that times out behind a proxy. This script
# produces the file; `POST /api/v1/dispatch/units/{unit}/packages` publishes the manifest
# that points devices at it.
#
# Everything here is open source and permissively licensed (CLAUDE.md rule 10):
#   - tippecanoe  (BSD-2-Clause)  vector tiles from GeoJSON
#   - pmtiles     (BSD-3-Clause)  single-file archive, no tile server needed
#
# Usage:
#   tools/tiles/build_pmtiles.sh <zone> <assets.geojson> <out-dir>
#
# The output is a single .pmtiles file. MapLibre reads it over HTTP range requests on the
# web, and the phone holds the whole file — which is the point: one file to copy, one hash
# to verify, and nothing to install in a truck.

set -euo pipefail

ZONE="${1:?falta la zona}"
ASSETS="${2:?falta el GeoJSON de activos}"
OUT_DIR="${3:?falta el directorio de salida}"

for tool in tippecanoe pmtiles; do
  command -v "$tool" >/dev/null 2>&1 || {
    echo "ERROR: falta '$tool' en el PATH." >&2
    echo "  tippecanoe: https://github.com/felt/tippecanoe (BSD-2-Clause)" >&2
    echo "  pmtiles:    https://github.com/protomaps/go-pmtiles (BSD-3-Clause)" >&2
    exit 127
  }
done

[ -f "$ASSETS" ] || { echo "ERROR: no existe '$ASSETS'." >&2; exit 1; }
mkdir -p "$OUT_DIR"

MBTILES="$OUT_DIR/$ZONE.mbtiles"
PMTILES="$OUT_DIR/$ZONE.pmtiles"

# -z16: a technician needs to tell one pole from the next, not read street numbers.
# --drop-densest-as-needed: a dense urban feeder must not blow the tile size limit and
#   silently lose features; dropping by density is visible and predictable.
# --no-tile-compression: the phone reads the archive directly and decompressing every tile
#   on a mid-range device costs more than the bytes saved.
tippecanoe \
  --output="$MBTILES" \
  --force \
  --layer="activos" \
  --minimum-zoom=10 \
  --maximum-zoom=16 \
  --drop-densest-as-needed \
  --no-tile-compression \
  --attribution="CNEL EP" \
  "$ASSETS"

pmtiles convert "$MBTILES" "$PMTILES"
rm -f "$MBTILES"

SIZE=$(wc -c < "$PMTILES")
HASH=$(sha256sum "$PMTILES" | cut -d' ' -f1)

echo "zona:   $ZONE"
echo "salida: $PMTILES"
echo "bytes:  $SIZE"
echo "sha256: $HASH"
echo
echo "Publicar el manifiesto:"
echo "  curl -X POST .../api/v1/dispatch/units/<UNIDAD>/packages \\"
echo "       -H 'Content-Type: application/json' \\"
echo "       -d '{\"zone\": \"$ZONE\", \"tile_url\": \"s3://.../$ZONE.pmtiles\", \"asset_count\": N}'"
