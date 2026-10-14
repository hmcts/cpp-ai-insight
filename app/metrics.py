import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from langchain_openai import AzureOpenAIEmbeddings
from ragas import evaluate
from ragas.metrics import BleuScore, RougeScore, answer_similarity

from app.config import get_azure_settings
from app.data import prepare_dataset

router = APIRouter()
logger = logging.getLogger(__name__)


def azure_openai_embeddings() -> AzureOpenAIEmbeddings:
    settings = get_azure_settings()
    return AzureOpenAIEmbeddings(
        model="text-embedding-ada-002",
        azure_deployment=settings.embedding_deployment,
        azure_endpoint=settings.endpoint,
        api_key=settings.api_key,
        api_version=settings.api_version,
    )


async def _score(request: Request, label: str, metric, score_key: str) -> float:
    """
    Run one local metric over the request body: 400 for a body that is not JSON, 422 when it cannot be turned into a
    dataset, 500 when the metric fails or returns no score.
    """
    logger.info("%s evaluation started", label)
    try:
        data = await request.json()
    except Exception as e:
        logger.error("Invalid JSON in request: %s", e)
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    try:
        dataset = prepare_dataset(data)
    except KeyError as e:
        logger.error("Missing required field in payload: %s", e)
        raise HTTPException(status_code=422, detail=f"Missing required field: {e}")
    except Exception as e:
        logger.error("Failed to prepare dataset: %s", e)
        raise HTTPException(status_code=422, detail=f"Dataset preparation failed: {e}")

    try:
        result = evaluate(dataset, metrics=[metric])
        score = result.scores[0].get(score_key)
        if score is None:
            logger.warning("%s score missing from result: %s", label, result.scores[0])
            raise HTTPException(status_code=500, detail=f"{label} score not found in evaluation result")
        logger.info("%s score: %s", label, score)
        return score
    except HTTPException:
        raise
    except Exception as e:
        logger.error("%s evaluation failed: %s", label, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"{label} evaluation failed: {e}")


@router.post("/bleu")
async def bleu_eval(request: Request) -> dict:
    return {"bleu": await _score(request, "BLEU", BleuScore(), "bleu_score")}


@router.post("/rouge")
async def rouge_eval(request: Request) -> dict:
    return {"rouge": await _score(request, "ROUGE", RougeScore(), "rouge_score(mode=fmeasure)")}


@router.post("/answerSimilarity")
async def answerSimilarity_eval(request: Request, embeddings=Depends(azure_openai_embeddings)):
    data = await request.json()
    dataset = prepare_dataset(data)
    result = evaluate(dataset, metrics=[answer_similarity], embeddings=embeddings)
    return {"answerSimilarity": result.scores[0].get("answer_similarity")}
