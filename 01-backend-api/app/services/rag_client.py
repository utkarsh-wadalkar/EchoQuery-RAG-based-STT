"""
RAG client — abstraction over the RAG engine.

Two implementations:
- ``MockRAGClient``:  Returns realistic fake answers (no external dependencies).
- ``HTTPRAGClient``:  Calls the real RAG engine API endpoint.

The backend picks the implementation based on ``settings.rag_endpoint``:
    - empty → mock
    - URL   → HTTP client
"""

from __future__ import annotations

import abc
import asyncio
import logging
import random
import time

import httpx

from ..schemas.query import QueryRequest, SupportedLanguage
from ..schemas.response import AnswerResponse, Latency, Source

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------

class RAGClient(abc.ABC):
    """Abstract RAG engine client."""

    @abc.abstractmethod
    async def query(self, request: QueryRequest) -> AnswerResponse:
        """Submit a query and return a grounded answer."""

    @abc.abstractmethod
    async def health_check(self) -> bool:
        """Return ``True`` if the RAG engine is reachable."""

    @abc.abstractmethod
    async def close(self) -> None:
        """Release resources."""

    @property
    @abc.abstractmethod
    def mode(self) -> str:
        """Human-readable label (``'mock'`` or ``'http'``)."""


# ---------------------------------------------------------------------------
# Mock implementation
# ---------------------------------------------------------------------------

_MOCK_ANSWERS: dict[SupportedLanguage, list[str]] = {
    SupportedLanguage.EN_IN: [
        (
            "Based on the retrieved documents, the engineering program requires "
            "a minimum of 75% aggregate in PCM (Physics, Chemistry, Mathematics) "
            "at the 12th standard level, along with a valid JEE Main score."
        ),
        (
            "The university offers several scholarship schemes including "
            "merit-based scholarships covering up to 100% tuition, "
            "need-based financial aid, and sports quota scholarships."
        ),
        (
            "According to the placement report, the average package for "
            "the 2024 batch was ₹12.5 LPA with the highest package reaching "
            "₹45 LPA.  Top recruiters include Google, Microsoft, and Amazon."
        ),
    ],
    SupportedLanguage.HI_IN: [
        (
            "प्राप्त दस्तावेजों के अनुसार, इंजीनियरिंग प्रोग्राम के लिए "
            "12वीं कक्षा में PCM में न्यूनतम 75% अंक और वैध JEE Main "
            "स्कोर आवश्यक है।"
        ),
    ],
}

_DEFAULT_ANSWER = (
    "Based on the available information, I can provide you with "
    "the following details regarding your query."
)

_MOCK_SOURCES = [
    Source(
        id="doc-001-chunk-3",
        text="The minimum eligibility criteria for admission is 75% aggregate...",
        score=0.92,
        metadata={"document": "admission_brochure.pdf", "page": 12},
    ),
    Source(
        id="doc-002-chunk-7",
        text="Scholarship details: Merit-based scholarships are awarded to...",
        score=0.87,
        metadata={"document": "scholarship_policy.pdf", "page": 3},
    ),
    Source(
        id="doc-003-chunk-1",
        text="Placement statistics for the batch of 2024 show an average...",
        score=0.81,
        metadata={"document": "placement_report_2024.pdf", "page": 1},
    ),
]


class MockRAGClient(RAGClient):
    """Returns realistic fake answers with simulated latency."""

    @property
    def mode(self) -> str:
        return "mock"

    async def health_check(self) -> bool:
        return True

    async def close(self) -> None:
        pass

    async def query(self, request: QueryRequest) -> AnswerResponse:
        t0 = time.perf_counter()

        # Simulate per-stage latency
        embedding_ms = random.uniform(5, 20)
        retrieval_ms = random.uniform(10, 40)
        reranking_ms = random.uniform(5, 15)
        generation_ms = random.uniform(30, 100)

        total_sim = (
            embedding_ms + retrieval_ms + reranking_ms + generation_ms
        ) / 1000
        await asyncio.sleep(total_sim)

        answers = _MOCK_ANSWERS.get(request.language, [_DEFAULT_ANSWER])
        answer_text = random.choice(answers)

        total_ms = (time.perf_counter() - t0) * 1000

        logger.info(
            "[MockRAG] request=%s total=%.1fms",
            request.request_id, total_ms,
        )

        return AnswerResponse(
            request_id=request.request_id,
            answer=answer_text,
            language=request.language,
            grounded=True,
            sources=random.sample(
                _MOCK_SOURCES, k=min(request.top_k, len(_MOCK_SOURCES)),
            ),
            latency=Latency(
                total_ms=round(total_ms, 1),
                embedding_ms=round(embedding_ms, 1),
                retrieval_ms=round(retrieval_ms, 1),
                reranking_ms=round(reranking_ms, 1),
                generation_ms=round(generation_ms, 1),
            ),
        )


# ---------------------------------------------------------------------------
# HTTP implementation (for when the AI team exposes their API)
# ---------------------------------------------------------------------------

class HTTPRAGClient(RAGClient):
    """Calls the real RAG engine over HTTP."""

    def __init__(self, endpoint: str, *, timeout: float = 30.0) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
        )

    @property
    def mode(self) -> str:
        return "http"

    async def health_check(self) -> bool:
        try:
            resp = await self._client.get(f"{self._endpoint}/health")
            return resp.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        await self._client.aclose()

    async def query(self, request: QueryRequest) -> AnswerResponse:
        payload = request.model_dump(mode="json")
        resp = await self._client.post(
            f"{self._endpoint}/api/v1/query",
            json=payload,
        )
        resp.raise_for_status()
        return AnswerResponse.model_validate(resp.json())


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_rag_client(
    *,
    endpoint: str = "",
    timeout: float = 30.0,
) -> RAGClient:
    """Create a RAG client.  Empty endpoint → mock."""
    if endpoint:
        logger.info("RAG client: HTTP → %s", endpoint)
        return HTTPRAGClient(endpoint, timeout=timeout)
    logger.info("RAG client: Mock (no RAG endpoint configured)")
    return MockRAGClient()
