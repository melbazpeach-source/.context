FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY pyproject.toml ./
COPY sirens_mcp_intelowl ./sirens_mcp_intelowl
RUN pip install .

USER 65534:65534
ENTRYPOINT ["sirens-mcp-intelowl"]
