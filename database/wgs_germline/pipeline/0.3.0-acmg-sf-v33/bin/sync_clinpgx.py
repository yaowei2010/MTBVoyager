#!/usr/bin/env python3
"""Download a versioned ClinPGx snapshot without sending patient data."""
import argparse
import datetime as dt
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path


def fetch_all(base, endpoint, size):
    page, records = 0, []
    while True:
        query = urllib.parse.urlencode({"page": page, "size": size})
        request = urllib.request.Request(f"{base.rstrip('/')}/{endpoint}?{query}", headers={"User-Agent": "MTB-ClinPGx-sync/1.0"})
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = json.load(response)
        data = payload.get("data", payload)
        content = data.get("content", data.get("data", data.get("results", []))) if isinstance(data, dict) else data
        records.extend(content)
        if not content or len(content) < size:
            return records
        page += 1
        time.sleep(0.55)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--base-url", default="https://api.pharmgkb.org/v1/data")
    parser.add_argument("--release", default=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d"))
    parser.add_argument("--page-size", type=int, default=100)
    args = parser.parse_args()
    target = Path(args.output) / args.release
    target.mkdir(parents=True, exist_ok=False)
    for name in ("variantAnnotation", "clinicalAnnotation"):
        rows = fetch_all(args.base_url, name, args.page_size)
        (target / f"{name}.json").write_text(json.dumps({"release": args.release, "data": rows}, indent=2) + "\n")
    (target / "manifest.json").write_text(json.dumps({
        "release": args.release, "source": args.base_url, "license": "CC BY-SA 4.0",
        "attribution": "ClinPGx/PharmGKB", "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
