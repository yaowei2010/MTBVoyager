#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
IMAGE=${FASTVEP_IMAGE:-mtb-fastvep:0.3.0-ac2e2b6}
COMMIT=${FASTVEP_COMMIT:-ac2e2b64a9c4c27163a3df16e0a559113af19625}

actual_commit=$(git -C "${ROOT_DIR}/src" rev-parse HEAD)
if [[ "${actual_commit}" != "${COMMIT}" ]]; then
    echo "ERROR: src is at ${actual_commit}; expected ${COMMIT}" >&2
    exit 1
fi

docker build \
    --build-arg "FASTVEP_COMMIT=${COMMIT}" \
    --build-arg FASTVEP_VERSION=0.3.0 \
    --tag "${IMAGE}" \
    "${ROOT_DIR}"

docker image inspect "${IMAGE}" --format 'Built {{.RepoTags}} ({{.Id}}, {{.Size}} bytes)'
