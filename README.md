# cpp-ai-insight

A small FastAPI service that scores LLM and RAG answers against a reference answer, using [ragas](https://docs.ragas.io) metrics. Other services and tests call it over HTTP, for example the AI search end-to-end tests in `cpp-ui-e2e-serenity`.

## Endpoints

| Method and path | Returns | Metric |
|---|---|---|
| `GET /` | `{"status": "ok"}` | Health check |
| `POST /bleu` | `{"bleu": <0..1>}` | ragas `BleuScore` (sacrebleu) |
| `POST /rouge` | `{"rouge": <0..1>}` | ragas `RougeScore`, ROUGE-L F-measure |
| `POST /answerSimilarity` | `{"answerSimilarity": <0..1>}` | ragas `answer_similarity`, using Azure OpenAI embeddings |

Each `POST` takes one JSON object (or a list of objects, in which case only the first object's score is returned):

```json
{
  "user_input": "What is the capital of France?",
  "response": "The capital of France is Paris.",
  "reference": "The capital of France is Paris."
}
```

```shell
curl -X POST localhost:4550/rouge -H 'Content-Type: application/json' \
  -d '{"user_input": "q", "response": "The capital of France is Paris.", "reference": "The capital of France is Paris."}'
# {"rouge":1.0}
```

Errors from `/bleu` and `/rouge` return `{"detail": "..."}`:

| Status | When |
|---|---|
| 400 | The body is not valid JSON |
| 422 | The body cannot be turned into rows (for example a plain string) |
| 500 | The metric fails, for example when `response` or `reference` is missing, or returns no score |

`/answerSimilarity` errors return 422 with `{"status": "error", "error_type": ..., "message": ...}`. The traceback is written to the log, not returned.

Logs are written to stdout as one JSON object per line.

Known issue: `/bleu` effectively scores only the first sentence of the response (DD-43812).

## Configuration

Only `/answerSimilarity` needs settings. It reads them from the environment:

| Variable | Purpose |
|---|---|
| `AZURE_OPENAI_API_KEY` | API key |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint |
| `AZURE_OPENAI_API_VERSION` | API version |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | Embedding deployment name |
| `PORT` | Port when run with `python -m app.main` (default 4550; the Docker image always uses 4550) |

## Running locally

Python 3.11, to match the Docker image.

```shell
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements-dev.txt

.venv/bin/uvicorn app.main:app --reload --port 4550
```

## Tests

```shell
.venv/bin/python -m pytest
```

The tests run the real ragas metrics. `/answerSimilarity` uses fake embeddings in tests, so no Azure access is needed.

## Docker

```shell
docker build -t cpp-ai-insight .
docker run -p 4550:4550 -e AZURE_OPENAI_API_KEY=... -e AZURE_OPENAI_ENDPOINT=... \
  -e AZURE_OPENAI_API_VERSION=... -e AZURE_OPENAI_EMBEDDING_DEPLOYMENT=... cpp-ai-insight
```

## CI

GitHub Actions (`.github/workflows/`):

| Workflow | Runs on | What it does |
|---|---|---|
| `ci.yml` | PRs and pushes to `main` | Installs `requirements-dev.txt`, runs the tests and pre-commit; builds the Docker image, starts it and runs `scripts/smoke-test.sh` against it |
| `codeql.yml` | PRs, pushes to `main` and weekly | CodeQL security analysis (`security-extended`) of the Python code and the workflows |
| `secrets-scanner.yml` | PRs and weekly | HMCTS secrets scanner (gitleaks) |

The smoke test can also be run against any running instance: `scripts/smoke-test.sh http://localhost:4550`.

## Dependencies

`requirements.txt` holds the runtime dependencies (the only file the image installs) and `requirements-dev.txt` the test tools. All direct dependencies are pinned; Renovate proposes upgrades through its dependency dashboard. `langchain-community` must stay below 0.4 (ragas fails to import with 0.4).

The service currently deployed is built from a copy of this code in `cpp-docker-images`. This repo keeps the same API, error responses and scores so it can replace that copy, using newer library versions.

## Contributing

We use pre-commit hooks for basic file checks (merge conflicts, whitespace, YAML and JSON syntax, private keys).
Install it with:

```shell
$ brew install pre-commit
$ pre-commit install
```

If you add a new hook make sure to run it against all files:
```shell
$ pre-commit run --all-files --show-diff-on-failure
```
