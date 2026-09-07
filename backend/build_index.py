"""
Phase 1 of the RAG pipeline - runs ONCE, at image build / deployment time.

    1. Load documents (PDFs in ./data)
    2. Split into chunks (800 chars, 200 overlap)
    3. Embed chunks (all-MiniLM-L6-v2)
    4. Store in Chroma, persisted to ./adwa_db_v2 on disk

The embedding model is also saved next to the app so serving never needs to
reach HuggingFace. Run with:

    python build_index.py

Nothing here is imported by the request path.
"""

import os
import sys
import time

import rag


def save_model_locally(embeddings):
    if os.path.isdir(rag.MODEL_DIR) and os.listdir(rag.MODEL_DIR):
        return

    os.makedirs(os.path.dirname(rag.MODEL_DIR) or ".", exist_ok=True)
    embeddings.save(rag.MODEL_DIR)
    print(f"Embedding model saved to {rag.MODEL_DIR}")


def main():
    started = time.time()

    if not os.path.isdir(rag.DATA_DIR):
        print(f"[ERROR] Data directory not found: {rag.DATA_DIR}")
        return 1

    pdfs = [name for name in os.listdir(rag.DATA_DIR) if name.lower().endswith(".pdf")]

    if not pdfs:
        print(f"[ERROR] No PDF files in {rag.DATA_DIR}")
        return 1

    print(f"Found {len(pdfs)} PDF file(s).")

    embeddings = rag.load_embeddings()
    save_model_locally(embeddings)

    rag.build_index(embeddings)

    print(f"Index build finished in {time.time() - started:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
