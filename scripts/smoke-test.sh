#!/usr/bin/env bash
# Smoke-test a running instance: health, a score from /bleu and /rouge, and the 400 for a body that is not JSON.
# /answerSimilarity is not called, as it needs Azure OpenAI.
# Usage: scripts/smoke-test.sh [base-url]   (default http://localhost:4550)
set -euo pipefail

BASE_URL="${1:-http://localhost:4550}"
BODY='{"user_input": "q", "response": "The capital of France is Paris.", "reference": "The capital of France is Paris."}'
failures=0

check() {
  local name="$1" expected_status="$2" expected_body="$3" actual_status actual_body
  shift 3
  actual_body=$(curl -s -o - -w '\n%{http_code}' "$@" || true)
  actual_status=$(tail -n1 <<< "$actual_body")
  actual_body=$(sed '$d' <<< "$actual_body")
  if [[ "$actual_status" == "$expected_status" && "$actual_body" == *"$expected_body"* ]]; then
    echo "PASS $name: $actual_status $actual_body"
  else
    echo "FAIL $name: expected $expected_status containing '$expected_body', got $actual_status $actual_body"
    failures=$((failures + 1))
  fi
}

check "health" 200 '"status":"ok"' "$BASE_URL/"
check "bleu" 200 '"bleu":1.0' -X POST "$BASE_URL/bleu" -H 'Content-Type: application/json' -d "$BODY"
check "rouge" 200 '"rouge":1.0' -X POST "$BASE_URL/rouge" -H 'Content-Type: application/json' -d "$BODY"
check "bleu invalid JSON" 400 'Invalid JSON payload' -X POST "$BASE_URL/bleu" -H 'Content-Type: application/json' -d 'not json'

if (( failures > 0 )); then
  echo "$failures smoke test(s) failed"
  exit 1
fi
echo "All smoke tests passed"
