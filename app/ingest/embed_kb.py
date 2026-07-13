"""Embed data/kb.json into a persisted Chroma collection.

Run: python -m app.ingest.embed_kb
"""
import json
from pathlib import Path

import chromadb

from app.config import settings
from app.llm.nvidia_client import embed

KB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "kb.json"
COLLECTION_NAME = "resolved_tickets"
BATCH_SIZE = 32


def load_kb() -> list[dict]:
    return json.loads(KB_PATH.read_text())


def get_collection():
    client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
    return client.get_or_create_collection(name=COLLECTION_NAME)


def main():
    records = load_kb()
    collection = get_collection()

    for start in range(0, len(records), BATCH_SIZE):
        batch = records[start:start + BATCH_SIZE]
        texts = [f"{r['title']}\n\n{r['description']}" for r in batch]
        vectors = embed(texts, input_type="passage")

        collection.upsert(
            ids=[r["id"] for r in batch],
            embeddings=vectors,
            documents=texts,
            metadatas=[
                {
                    "title": r["title"],
                    "description": r["description"],
                    "resolution_notes": r["resolution_notes"],
                    "risk_tier": r["risk_tier"],
                    "resolved_by_team": r["resolved_by_team"],
                    "category": r["category"],
                }
                for r in batch
            ],
        )
        print(f"Upserted {len(batch)} records ({start + len(batch)}/{len(records)})")

    print(f"Done. Collection '{COLLECTION_NAME}' has {collection.count()} records.")


if __name__ == "__main__":
    main()
