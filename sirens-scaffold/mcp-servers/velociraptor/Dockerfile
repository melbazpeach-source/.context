FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml ./
COPY sirens_mcp_velociraptor ./sirens_mcp_velociraptor
RUN pip install .

USER 65534:65534
ENTRYPOINT ["sirens-mcp-velociraptor"]
