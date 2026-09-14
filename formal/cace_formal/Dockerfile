FROM ubuntu:24.04

ARG LEAN_VERSION=4.32.1
ARG LEAN_SHA256=57d5c062a6b4bae6fba511a1704aa124dff461c37d0fc94585637fbb7d951b50

RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl git zstd build-essential && \
    rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    curl -fL "https://github.com/leanprover/lean4/releases/download/v${LEAN_VERSION}/lean-${LEAN_VERSION}-linux.tar.zst" \
      -o /tmp/lean.tar.zst; \
    echo "${LEAN_SHA256}  /tmp/lean.tar.zst" | sha256sum -c -; \
    mkdir -p /opt/lean; \
    tar --use-compress-program=unzstd -xf /tmp/lean.tar.zst -C /opt/lean --strip-components=1; \
    rm /tmp/lean.tar.zst

ENV PATH="/opt/lean/bin:${PATH}"
WORKDIR /work
COPY . /work

RUN lean --version && lake --version
RUN lake update && lake exe cache get && lake build CACEFormal
