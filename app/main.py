#!/usr/bin/env python3
import logging
import os

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.metrics import router as metrics_router

logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
    datefmt="%Y-%m-%dT%H:%M:%S",
)

app = FastAPI(title="RAGAS Evaluation API", version="1.0.0")
app.include_router(metrics_router)
logger = logging.getLogger(__name__)


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch all unhandled exceptions and return a JSON error response.

    The traceback is logged, not returned, so stack traces are not exposed to callers.
    """
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "error_type": exc.__class__.__name__,
            "message": str(exc),
        },
    )


@app.get("/")
def read_root() -> dict:
    logger.info("Reading root endpoint")
    return {"status": "ok"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 4550))
    uvicorn.run(app, host="0.0.0.0", port=port)
