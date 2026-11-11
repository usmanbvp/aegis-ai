from app.synthetic_data import build_document_corpus
from app.rag.retrieval import RetrievalService


def test_retrieval_search_returns_service_relevant_documents() -> None:
    documents = build_document_corpus()
    service = RetrievalService(documents=documents)

    results = service.search("cache invalidation storm", limit=5)

    assert results
    assert any(result["service"] == "inventory-api" for result in results)
    assert any("cache" in result["content"].lower() for result in results)


def test_retrieval_can_filter_by_service() -> None:
    documents = build_document_corpus()
    service = RetrievalService(documents=documents)

    results = service.search("timeout", service="checkout-api", limit=3)

    assert results
    assert all(result["service"] == "checkout-api" for result in results)
