#!/usr/bin/env python3
"""Download the SGB risk sectors for Porto Alegre, validate them, and write a versioned envelope.

Used in two places:
- Clarus repo: refreshes the snapshot bundled in the app (`--source mirror`).
- clarus-data repo: refreshes the public fallback copy (`--source official --previous ... --always-write`).

Exit codes: 0 = written or unchanged, 1 = download or validation failed (nothing written).
Only the Python standard library is used.
"""

import argparse
import hashlib
import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1
MAX_DROP_RATIO = 0.20
SOURCE = "SGB — Serviço Geológico do Brasil (geoportal.sgb.gov.br)"
OFFICIAL_ENDPOINT = "https://geoportal.sgb.gov.br/server/rest/services/gestaoterritorial/risco/FeatureServer/0/query"
OFFICIAL_PARAMS = {
    "where": "cd_geocmu='4314902'",
    "outFields": "grau_risco,local,tipolo_g1,tipolo_e1,num_pess,num_domi,num_edif,data_setor,munic,uf",
    "returnGeometry": "true",
    "outSR": "4326",
    "f": "json",
}
OFFICIAL_QUERY = OFFICIAL_ENDPOINT + "?" + urllib.parse.urlencode(OFFICIAL_PARAMS)
MIRROR_URL = "https://clarus-org.github.io/clarus-data/sgb/porto-alegre/risk-sectors.json"


def validate(arcgis, previous_count, force):
    """Raise ValueError when the response must not replace the current copy.

    `force` skips only the drop guard; empty, truncated, or polygon-less data is never accepted.
    """
    features = arcgis.get("features") if isinstance(arcgis, dict) else None
    if not isinstance(features, list):
        raise ValueError("response has no 'features' list")
    if not features:
        raise ValueError("response has no features")
    if arcgis.get("exceededTransferLimit") is True:
        raise ValueError("response was truncated (exceededTransferLimit)")
    for index, feature in enumerate(features):
        if not isinstance(feature, dict) or not isinstance(feature.get("attributes"), dict):
            raise ValueError(f"feature {index} has no attributes")
        geometry = feature.get("geometry")
        rings = geometry.get("rings") if isinstance(geometry, dict) else None
        if not isinstance(rings, list) or not rings or not rings[0]:
            raise ValueError(f"feature {index} has no polygon")
    if previous_count and not force and len(features) < previous_count * (1 - MAX_DROP_RATIO):
        raise ValueError(
            f"feature count dropped from {previous_count} to {len(features)} (> {int(MAX_DROP_RATIO * 100)}%); "
            "rerun with --force if the drop is legitimate"
        )


def canonical_sha256(arcgis):
    canonical = json.dumps(arcgis, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_envelope(arcgis, query, fetched_at):
    return {
        "schemaVersion": SCHEMA_VERSION,
        "source": SOURCE,
        "query": query,
        "fetchedAt": fetched_at,
        "featureCount": len(arcgis["features"]),
        "sha256": canonical_sha256(arcgis),
        "arcgis": arcgis,
    }


def fetch_json(url):
    request = urllib.request.Request(url, headers={"User-Agent": "clarus-sgb-snapshot/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        if response.status != 200:
            raise ValueError(f"HTTP {response.status} from {url}")
        return json.load(response)


def read_envelope(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def now_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", choices=("official", "mirror"), required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--previous", help="envelope used as reference for the 20%% drop guard")
    parser.add_argument("--force", action="store_true", help="skip only the drop guard")
    parser.add_argument(
        "--always-write",
        action="store_true",
        help="rewrite even when the data is unchanged (refreshes fetchedAt)",
    )
    args = parser.parse_args(argv)

    try:
        if args.source == "official":
            arcgis, query, fetched_at = fetch_json(OFFICIAL_QUERY), OFFICIAL_QUERY, now_utc()
        else:
            mirror = fetch_json(MIRROR_URL)
            if mirror.get("schemaVersion") != SCHEMA_VERSION:
                raise ValueError(f"unsupported mirror schemaVersion {mirror.get('schemaVersion')}")
            arcgis, query, fetched_at = mirror["arcgis"], mirror["query"], mirror["fetchedAt"]

        previous = read_envelope(args.previous) if args.previous else None
        validate(arcgis, previous.get("featureCount") if previous else None, args.force)
    except Exception as error:  # network, HTTP, JSON, or validation
        print(f"error: {error}", file=sys.stderr)
        return 1

    envelope = build_envelope(arcgis, query, fetched_at)
    current = read_envelope(args.out)
    if current and current.get("sha256") == envelope["sha256"] and not args.always_write:
        print(f"unchanged featureCount={envelope['featureCount']}")
        return 0

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(envelope, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"updated featureCount={envelope['featureCount']} fetchedAt={fetched_at}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
