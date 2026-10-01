#!/usr/bin/env python3
"""Merge chromosome-scattered VEP tabular gzip outputs deterministically."""
import argparse
import gzip
import re
from pathlib import Path


PRIMARY = [f"chr{i}" for i in range(1, 23)] + ["chrX", "chrY", "chrM", "other"]
RANK = {name: index for index, name in enumerate(PRIMARY)}


def shard_name(path, sample):
    match = re.match(rf"{re.escape(sample)}\.(.+)\.vep\.tsv\.gz$", Path(path).name)
    if not match:
        raise ValueError(f"Unexpected VEP shard filename: {path}")
    return match.group(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("shards", nargs="+")
    args = parser.parse_args()
    ordered = sorted(args.shards, key=lambda path: RANK.get(shard_name(path, args.sample), 999))
    header_written = False
    schema = None
    names = [shard_name(path, args.sample) for path in ordered]
    if len(set(names)) != len(names):
        raise ValueError("Duplicate annotation shards")
    with gzip.open(args.output, "wt") as output:
        for path in ordered:
            with gzip.open(path, "rt", errors="strict") as source:
                shard_schema = None
                for line in source:
                    if line.startswith("#Uploaded_variation"):
                        shard_schema = line.rstrip("\n").split("\t")
                        if schema is None:
                            schema = shard_schema
                        elif schema != shard_schema:
                            raise ValueError(f"Annotation shard columns differ: {path}")
                    if line.startswith("#"):
                        if not header_written:
                            output.write(line)
                    else:
                        if shard_schema is None or len(line.rstrip("\n").split("\t")) != len(schema):
                            raise ValueError(f"Malformed annotation shard: {path}")
                        output.write(line)
                if shard_schema is None:
                    raise ValueError(f"Annotation shard header is absent: {path}")
            header_written = True


if __name__ == "__main__":
    main()
