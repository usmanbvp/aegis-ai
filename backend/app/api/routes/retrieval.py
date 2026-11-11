from __future__ import annotations

from fastapi import APIRouter, Query

from app.rag.retrieval import RetrievalService
from app.synthetic_data import build_document_corpus

router = APIRouter(prefix="/api/v1/retrieval", tags=["retrieval"])


@router.get("/search")
def search_documents(
    q: str = Query(..., min_length=1),
    service: str | None = None,
    limit: int = Query(default=5, ge=1, le=20),
) -> dict[str, object]:
    documents = build_document_corpus()
    service_obj = RetrievalService(documents=documents)
    return {
        "query": q,
        "service": service,
        "results": service_obj.search(q, service=service, limit=limit),
    }


@router.post("/index")
def index_documents() -> dict[str, object]:
    documents = build_document_corpus()
    service = RetrievalService(documents=documents)
    return {
        "indexed_documents": len(service.documents),
        "status": "ok",
    }
