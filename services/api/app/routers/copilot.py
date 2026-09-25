"""AI Copilot endpoint (local Ollama only)."""

from typing import Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth import viewer
from ..copilot.agent import ask

router = APIRouter(tags=["copilot"])


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    lang: Literal["en", "hi"] = "en"


@router.post("/copilot/ask")
async def copilot_ask(q: Question, _user: dict = Depends(viewer)) -> dict:
    """Answer + the SQL it ran + the rows used + a chart spec. Uses local Ollama qwen2.5:7b."""
    try:
        return await ask(q.question, q.lang)
    except httpx.HTTPError as e:
        raise HTTPException(
            503,
            f"Local Ollama is not reachable ({e.__class__.__name__}). "
            "Start it with `brew services start ollama`.",
        ) from e
