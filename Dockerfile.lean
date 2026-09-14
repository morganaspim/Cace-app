FROM ubuntu:24.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl git zstd build-essential \
    && rm -rf /var/lib/apt/lists/*

ARG LEAN_URL=https://github.com/leanprover/lean4/releases/download/v4.32.1/lean-4.32.1-linux.tar.zst
ARG LEAN_SHA256=57d5c062a6b4bae6fba511a1704aa124dff461c37d0fc94585637fbb7d951b50

RUN curl -L "$LEAN_URL" -o /tmp/lean.tar.zst \
    && echo "$LEAN_SHA256  /tmp/lean.tar.zst" | sha256sum -c - \
    && mkdir -p /opt/lean \
    && tar --use-compress-program=unzstd -xf /tmp/lean.tar.zst -C /opt/lean --strip-components=1 \
    && rm /tmp/lean.tar.zst

ENV PATH="/opt/lean/bin:${PATH}"
WORKDIR /cace
COPY . /cace

RUN lean --version
RUN lake --version

WORKDIR /cace/formal/cace_formal
RUN lake update
RUN lake exe cache get
RUN lake build CACEFormal
