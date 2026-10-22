FROM rust:bookworm AS builder

ARG FASTVEP_COMMIT=ac2e2b64a9c4c27163a3df16e0a559113af19625
ENV RUSTUP_TOOLCHAIN=1.98.1-x86_64-unknown-linux-gnu
WORKDIR /build/fastvep

COPY src/Cargo.toml src/Cargo.lock src/rust-toolchain.toml ./
COPY src/crates ./crates
COPY src/web ./web

RUN test "$(git rev-parse --is-inside-work-tree 2>/dev/null || true)" != "true" || \
    test "$(git rev-parse HEAD)" = "${FASTVEP_COMMIT}"
RUN cargo build --release --locked \
    --package fastvep-cli \
    --package fastvep-web

FROM debian:bookworm-slim AS runtime

ARG FASTVEP_VERSION=0.3.0
ARG FASTVEP_COMMIT=ac2e2b64a9c4c27163a3df16e0a559113af19625

LABEL org.opencontainers.image.title="MTB fastVEP PoC" \
      org.opencontainers.image.description="Standalone fastVEP CLI and web service for validation outside the MTB production pipeline" \
      org.opencontainers.image.version="${FASTVEP_VERSION}" \
      org.opencontainers.image.revision="${FASTVEP_COMMIT}" \
      org.opencontainers.image.source="https://github.com/Huang-lab/fastVEP" \
      org.opencontainers.image.licenses="Apache-2.0"

RUN apt-get update && \
    apt-get install --yes --no-install-recommends ca-certificates tini && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd --gid 10001 fastvep && \
    useradd --uid 10001 --gid fastvep --create-home --shell /usr/sbin/nologin fastvep && \
    mkdir -p /data/reference /data/sa /work /opt/fastvep/tests && \
    chown -R fastvep:fastvep /work /home/fastvep

COPY --from=builder /build/fastvep/target/release/fastvep /usr/local/bin/fastvep
COPY --from=builder /build/fastvep/target/release/fastvep-web /usr/local/bin/fastvep-web
COPY src/tests/test.vcf src/tests/test.gff3 /opt/fastvep/tests/

USER fastvep
WORKDIR /work
EXPOSE 8080

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["fastvep", "--help"]
