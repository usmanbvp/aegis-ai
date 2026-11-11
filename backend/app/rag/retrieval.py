from __future__ import annotations

import re
from typing import Any, Iterable

from app.synthetic_data import DocumentRecord, build_document_corpus

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, PointStruct, VectorParams
except Exception:  # pragma: no cover - optional dependency
    QdrantClient = None
    Distance = None
    PointStruct = None
    VectorParams = None


class RetrievalService:
    def __init__(self, documents: Iterable[DocumentRecord] | None = None) -> None:
        self.documents = list(documents) if documents is not None else build_document_corpus()
        self._index = self._build_index(self.documents)

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return {
            token.lower()
            for token in re.findall(r"[a-z0-9]+", (text or "").lower())
            if len(token) > 2
        }

    def _build_index(self, documents: list[DocumentRecord]) -> dict[str, dict[str, Any]]:
        index: dict[str, dict[str, Any]] = {}
        for document in documents:
            index[document.document_id] = {
                "document": document,
                "tokens": self._tokenize(f"{document.title} {' '.join(document.tags)} {document.content}"),
            }
        return index

    def _score_document(self, document: DocumentRecord, query_tokens: set[str]) -> float:
        if not query_tokens:
            return 0.0

        content = f"{document.title} {' '.join(document.tags)} {document.content}".lower()
        title_tokens = self._tokenize(document.title)
        overlap = len(query_tokens & self._tokenize(content))
        title_bonus = 4 * len(query_tokens & title_tokens)
        service_bonus = 2.0 if document.service and document.service in content else 0.0
        return float(overlap + title_bonus + service_bonus)

    def search(self, query: str, service: str | None = None, limit: int = 5) -> list[dict[str, Any]]:
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        scored: list[tuple[float, DocumentRecord]] = []
        for document in self.documents:
            if service and document.service != service:
                continue
            score = self._score_document(document, query_tokens)
            if score > 0:
                scored.append((score, document))

        scored.sort(key=lambda item: item[0], reverse=True)
        results: list[dict[str, Any]] = []
        for score, document in scored[:limit]:
            results.append(
                {
                    "document_id": document.document_id,
                    "title": document.title,
                    "service": document.service,
                    "document_type": document.document_type,
                    "score": round(score, 3),
                    "content": document.content[:400],
                    "tags": document.tags,
                }
            )
        return results

    def index_documents(self, documents: Iterable[DocumentRecord] | None = None) -> None:
        if documents is not None:
            self.documents = list(documents)
        self._index = self._build_index(self.documents)

    def search_with_optional_qdrant(
        self,
        query: str,
        *,
        service: str | None = None,
        limit: int = 5,
        qdrant_url: str | None = None,
    ) -> list[dict[str, Any]]:
        if QdrantClient is not None and qdrant_url:
            try:
                client = QdrantClient(url=qdrant_url)
                if client.get_collection(collection_name="aegis-documents"):
                    return self.search(query, service=service, limit=limit)
            except Exception:
                pass
        return self.search(query, service=service, limit=limit)
