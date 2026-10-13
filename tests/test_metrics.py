import pytest

SAMPLE = {
    "user_input": "What is the capital of France?",
    "response": "The capital of France is Paris.",
    "reference": "The capital of France is Paris.",
}
MISMATCH = {**SAMPLE, "response": "Bananas grow on tall green plants."}


def test_root_returns_ok(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize(
    "path, key",
    [("/bleu", "bleu"), ("/rouge", "rouge"), ("/answerSimilarity", "answerSimilarity")],
)
def test_identical_response_and_reference_scores_one(client, path, key):
    response = client.post(path, json=SAMPLE)

    assert response.status_code == 200
    assert response.json()[key] == pytest.approx(1.0)


@pytest.mark.parametrize("path, key", [("/bleu", "bleu"), ("/rouge", "rouge")])
def test_unrelated_response_scores_low(client, path, key):
    response = client.post(path, json=MISMATCH)

    assert response.status_code == 200
    assert response.json()[key] < 0.2


def test_list_body_returns_first_row_score(client):
    response = client.post("/rouge", json=[SAMPLE, MISMATCH])

    assert response.status_code == 200
    assert response.json()["rouge"] == pytest.approx(1.0)


LOCAL_METRICS = [("/bleu", "BLEU"), ("/rouge", "ROUGE")]


@pytest.mark.parametrize("path, label", LOCAL_METRICS)
def test_body_that_is_not_json_returns_400(client, path, label):
    response = client.post(path, content="not json", headers={"Content-Type": "application/json"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid JSON payload"


@pytest.mark.parametrize("path, label", LOCAL_METRICS)
def test_body_that_is_not_rows_returns_422(client, path, label):
    response = client.post(path, json="just a string")

    assert response.status_code == 422
    assert response.json()["detail"].startswith("Dataset preparation failed")


@pytest.mark.parametrize("path, label", LOCAL_METRICS)
def test_missing_columns_return_500(client, path, label):
    response = client.post(path, json={"unexpected": "field"})

    assert response.status_code == 500
    assert response.json()["detail"].startswith(f"{label} evaluation failed")


@pytest.mark.parametrize("path, label", LOCAL_METRICS)
def test_missing_score_returns_500(client, monkeypatch, path, label):
    class NoScores:
        scores = [{}]

    monkeypatch.setattr("app.metrics.evaluate", lambda dataset, metrics: NoScores())

    response = client.post(path, json=SAMPLE)

    assert response.status_code == 500
    assert response.json()["detail"] == f"{label} score not found in evaluation result"


def test_unhandled_error_returns_422_error_payload(client):
    response = client.post("/answerSimilarity", json={"unexpected": "field"})

    assert response.status_code == 422
    body = response.json()
    assert body["status"] == "error"
    assert body["error_type"]
    assert isinstance(body["trace"], list)


def test_scores_are_logged(client, caplog):
    with caplog.at_level("INFO", logger="app.metrics"):
        client.post("/rouge", json=SAMPLE)

    assert "ROUGE evaluation started" in caplog.text
    assert "ROUGE score: 1.0" in caplog.text
