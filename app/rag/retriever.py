import chromadb

from app.config import settings
from app.llm.nvidia_client import embed
from app.schemas import KBRecord, RetrievedRecord

COLLECTION_NAME = "resolved_tickets"

_client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
_collection = _client.get_or_create_collection(name=COLLECTION_NAME)


def retrieve(ticket_title: str, ticket_description: str, k: int = 4) -> list[RetrievedRecord]:
    query_text = f"{ticket_title}\n\n{ticket_description}"
    query_vector = embed([query_text], input_type="query")[0]

    results = _collection.query(query_embeddings=[query_vector], n_results=k)

    retrieved = []
    ids = results["ids"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    for doc_id, meta, dist in zip(ids, metadatas, distances):
        record = KBRecord(
            id=doc_id,
            title=meta["title"],
            description=meta["description"],
            resolution_notes=meta["resolution_notes"],
            risk_tier=meta["risk_tier"],
            resolved_by_team=meta["resolved_by_team"],
            category=meta["category"],
        )
        # Chroma returns squared-L2 distance; convert to a 0-1 similarity score.
        similarity = 1.0 / (1.0 + dist)
        retrieved.append(RetrievedRecord(record=record, similarity=similarity))

    return retrieved
