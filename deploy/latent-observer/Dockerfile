FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN pip install --no-cache-dir "numpy>=2.0" \
    && useradd --system --uid 10001 --create-home observer
WORKDIR /opt/cace-observer
COPY cace_studio /opt/cace-observer/cace_studio
USER observer
ENTRYPOINT ["python", "-m", "cace_studio.ai.latent_observer_worker"]
