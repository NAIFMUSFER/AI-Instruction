# One job container: no network, read-only root, bounded CPU/RAM/PIDs (worker.mjs).
FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl xz-utils libx11-6 libxi6 libxrender1 libxfixes3 libxkbcommon0 libsm6 libice6 libgl1 libegl1 libgomp1 && rm -rf /var/lib/apt/lists/*
ARG BLENDER_VERSION=4.5.13
RUN mkdir -p /opt/blender && cd /tmp && \
    curl --fail --location --retry 2 -O https://download.blender.org/release/Blender4.5/blender-${BLENDER_VERSION}-linux-x64.tar.xz && \
    curl --fail --location --retry 2 -O https://download.blender.org/release/Blender4.5/blender-${BLENDER_VERSION}.sha256 && \
    grep "blender-${BLENDER_VERSION}-linux-x64.tar.xz$" blender-${BLENDER_VERSION}.sha256 | sha256sum -c - && \
    tar -xf blender-${BLENDER_VERSION}-linux-x64.tar.xz --strip-components=1 -C /opt/blender && rm /tmp/blender-*
COPY render-worker/build_scene.py /opt/masar/build_scene.py
ENV PATH="/opt/blender:${PATH}" HOME=/tmp OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
USER 1000:1000
ENTRYPOINT ["blender"]
