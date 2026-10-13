# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

A small FastAPI service ("RAGAS Evaluation API") that wraps [ragas](https://docs.ragas.io) metrics behind HTTP endpoints, so other services can score LLM/RAG outputs. The code is in the `app/` package and the tests are in `tests/`.

## Commands

```shell
# Set up (Python 3.11, to match the Docker image)
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements-dev.txt

# Run locally (port from $PORT, default 4550)
.venv/bin/python -m app.main
# or, with reload
.venv/bin/uvicorn app.main:app --reload --port 4550

# Tests
.venv/bin/python -m pytest
.venv/bin/python -m pytest tests/test_metrics.py::test_list_body_returns_first_row_score   # single test

# Docker (the image always listens on 4550 and ignores $PORT)
docker build -t cpp-ai-insight .
docker run -p 4550:4550 -e AZURE_OPENAI_API_KEY=... cpp-ai-insight

# Pre-commit hooks (whitespace, YAML/JSON checks, private-key detection)
pre-commit install
pre-commit run --all-files --show-diff-on-failure
```

`requirements.txt` lists only runtime dependencies and is the only file the Docker image installs. Test and development tools go in `requirements-dev.txt`. Every direct dependency is pinned to an exact version, so each image build gets the same metric implementations; Renovate (`renovate.json`, approval through the dependency dashboard) proposes upgrades. Import a package directly only if it is listed (for example `datasets`, used by `app/data.py`), rather than relying on it arriving through ragas.

## Architecture

- `app/main.py` creates the FastAPI app, the global exception handler and the `/` health route, and includes the router from `app/metrics.py`.
- Each metric endpoint (`POST /bleu`, `/rouge`, `/answerSimilarity`) takes a raw JSON body, either one object or a list of objects. `app/data.py:prepare_dataset` turns that into a HuggingFace `Dataset`, and `ragas.evaluate` runs one metric over it. Only `result.scores[0]` (the **first** row's score) is returned, so the score for any later row in a list is dropped. A test covers this current behaviour.
- The input rows must use ragas's column names (`user_input`, `response`, `reference`). The request body has no Pydantic model, so the API does not validate input itself; ragas raises the error instead.
- `/bleu` and `/rouge` share `app/metrics.py:_score`, which returns `{"detail": ...}` errors: **400** `Invalid JSON payload` for a body that is not JSON, **422** `Dataset preparation failed: ...` when the body cannot be turned into a dataset, and **500** `<METRIC> evaluation failed: ...` when the metric fails (including missing columns) or `<METRIC> score not found in evaluation result` when it returns no score.
- `/answerSimilarity` has no error handling of its own. A global exception handler turns any unhandled exception into an HTTP **422** with `status`, `error_type`, `message` and the last 5 lines of the traceback.
- Logging goes to stdout as one JSON object per line (`logging.basicConfig` in `app/main.py`); each module logs through `logging.getLogger(__name__)`.

## Compatibility with the deployed service

The service currently deployed is built from a separate copy of the code in `cpp-docker-images` (`dependencies/ai-insight/cpp_ai_insight_api.py`, with its own requirements file and Dockerfile). This repo is meant to replace it, so keep the two compatible: the same routes, request bodies, response keys, status codes and error messages, and the same scores. `requirements.txt` uses newer versions than the deployed build (ragas 0.4.3 rather than 0.3.4, and so on); before any version change, check that `/bleu`, `/rouge` and `/answerSimilarity` give the same scores on both. The one deliberate difference is that the deployed copy overwrites the `AZURE_OPENAI_*` variables with empty strings on import; this repo reads them instead. Any other behaviour change (for example the BLEU fix, DD-43812) must be a conscious, documented change.
- `/answerSimilarity` is the only endpoint that calls an external service. It uses Azure OpenAI embeddings, which it gets through the `azure_openai_embeddings` FastAPI dependency. That dependency reads its settings with `app/config.py:get_azure_settings`, which takes the `AZURE_OPENAI_API_KEY`, `_ENDPOINT`, `_API_VERSION` and `_EMBEDDING_DEPLOYMENT` environment variables and caches the result with `lru_cache`. BLEU and ROUGE run locally (`sacrebleu`, `rouge-score`).

## CI

`.github/workflows/ci.yml` runs on PRs and pushes to `main`: tests and pre-commit on Python 3.11, then a Docker build, container start and `scripts/smoke-test.sh` (health, `/bleu`, `/rouge`, the 400 for invalid JSON; not `/answerSimilarity`, which needs Azure). `codeql.yml` (Python and Actions, `security-extended`) and `secrets-scanner.yml` (HMCTS gitleaks; needs the `GITLEAKS_LICENSE` and `HMCTS_CP_GITLEAKS_REGEX_INTERNAL_URL` secrets) run on PRs and weekly. The workflows only build and test; nothing publishes an image yet.

## Testing

- The tests run real ragas metrics, with no mocks. For `/answerSimilarity`, `tests/conftest.py` replaces the Azure dependency with a `FakeEmbeddings` class via `app.dependency_overrides`, so no network access or credentials are needed. Use the same override pattern for any new endpoint that calls an external service.
- `get_azure_settings` is cached, so call `get_azure_settings.cache_clear()` after changing the environment in a test.

## Gotchas

- Don't name modules in `app/` after third-party packages. For example, a file called `datasets.py` shadows HuggingFace `datasets` when `app/` ends up on `sys.path`.
- `langchain-community` must stay below `0.4`: from 0.4 it drops `langchain_community.chat_models.vertexai`, and `import ragas` fails.
- ragas 0.4 deprecates the `ragas.metrics` imports, `evaluate()` and the LangChain embeddings wrapper used here. They still work (the tests show the warnings), but ragas 1.0 removes them.
