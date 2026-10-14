# Build the wheel, the same artefact a release publishes to Azure Artifacts.
FROM python:3.11-slim AS build

WORKDIR /src

# The build context has no .git, so setuptools-scm cannot read the version from a tag.
ARG VERSION=0.0.0
ENV SETUPTOOLS_SCM_PRETEND_VERSION=${VERSION}

COPY pyproject.toml requirements.txt README.md LICENSE ./
COPY app/ ./app/
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /dist .

# Use slim Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (optional, for numpy/pandas performance)
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install the service and its pinned dependencies from the wheel
COPY --from=build /dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl

# Expose FastAPI port
EXPOSE 4550

# Run FastAPI with Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "4550"]
