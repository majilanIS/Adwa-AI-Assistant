"""
Shared RAG pieces, split into the two phases of the pipeline.

Phase 1 (one-time, at image build / deployment time):
    load documents -> split into chunks -> embed chunks -> store in Chroma
    See build_index.py, which is executed during `docker build`.

Phase 2 (per request, at serving time):
    embed query -> similarity search -> build prompt -> LLM -> JSON response
    See app.py.

At serving time this module only *loads* what phase 1 already produced, so a
request never pays for model downloads or document embedding.
"""

import os
import re
import shutil

from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.runnables import RunnableLambda
from sentence_transformers import SentenceTransformer

from prompt import prompt

# ========================
# Configuration
# ========================

DATA_DIR = os.getenv("DATA_DIR", "./data")
PERSIST_DIR = os.getenv("VECTOR_DB_DIR", "./adwa_db_v2")

# Directory holding the sentence-transformers model baked into the image.
# When it is present the model is loaded from disk, so no HuggingFace download
# happens at serving time.
MODEL_DIR = os.getenv("EMBEDDING_MODEL_DIR", "./models/all-MiniLM-L6-v2")
MODEL_NAME = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
TOP_K = int(os.getenv("RETRIEVER_TOP_K", "6"))
RETRIEVE_CANDIDATES = int(os.getenv("RETRIEVE_CANDIDATES", "16"))
EMBED_BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", "64"))

# llama-3.1-8b-instant was decommissioned by Groq and now returns 404.
# openai/gpt-oss-20b is the current fast instruction-following model on Groq;
# openai/gpt-oss-120b is the stronger, slower alternative.
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-20b")
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "30"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "1"))

# Phase 1 belongs to the build. If the index is missing at serving time we would
# rather fail loudly than silently spend minutes embedding inside a request, but
# local development (`python app.py` with no prebuilt index) still needs it.
ALLOW_RUNTIME_BUILD = os.getenv("ALLOW_RUNTIME_INDEX_BUILD", "1") != "0"


class SentenceTransformerEmbeddings:

    def __init__(self, model_name_or_path):
        self._model = SentenceTransformer(model_name_or_path)

    def embed_documents(self, texts):
        return self._model.encode(
            texts,
            batch_size=EMBED_BATCH_SIZE,
            convert_to_tensor=False,
            normalize_embeddings=True,
            show_progress_bar=False
        ).tolist()

    def embed_query(self, text):
        return self._model.encode(
            [text],
            convert_to_tensor=False,
            normalize_embeddings=True
        )[0].tolist()

    def save(self, target_dir):
        self._model.save(target_dir)


def load_embeddings():
    """Load the embedding model, preferring the copy baked into the image."""
    if os.path.isdir(MODEL_DIR) and os.listdir(MODEL_DIR):
        print(f"Loading embedding model from {MODEL_DIR}")
        return SentenceTransformerEmbeddings(MODEL_DIR)

    print(f"Downloading embedding model {MODEL_NAME}")
    return SentenceTransformerEmbeddings(MODEL_NAME)


def index_exists(persist_directory=PERSIST_DIR):
    return os.path.isdir(persist_directory) and bool(os.listdir(persist_directory))


# ========================
# Phase 1 - one-time initialization
# ========================

def build_index(embeddings=None, data_dir=DATA_DIR, persist_directory=PERSIST_DIR):
    """Load PDFs, split them, embed the chunks and persist the Chroma database.

    This is the expensive step (minutes on CPU) and is meant to run once, at
    build time - never inside a user request.
    """
    embeddings = embeddings or load_embeddings()

    if os.path.exists(persist_directory):
        shutil.rmtree(persist_directory, ignore_errors=True)

    print(f"Loading documents from {data_dir}")
    loader = PyPDFDirectoryLoader(path=data_dir, glob="*.pdf")
    documents = loader.load()
    print(f"Loaded {len(documents)} pages.")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )
    chunks = splitter.split_documents(documents)
    print(f"Split into {len(chunks)} chunks.")

    for i, doc in enumerate(chunks):
        source = doc.metadata.get("source") or f"Document-{i + 1}"
        doc.metadata["source"] = os.path.basename(source)

    print("Embedding chunks and writing vector database...")
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=persist_directory
    )

    # chromadb < 0.4.x needs an explicit flush; newer versions persist on write.
    persist = getattr(vectorstore, "persist", None)
    if callable(persist):
        try:
            persist()
        except Exception as error:  # pragma: no cover - version dependent
            print("[WARN] Explicit persist not supported:", error)

    print(f"Vector database created at {persist_directory}.")
    return vectorstore


def load_vectorstore(embeddings, persist_directory=PERSIST_DIR):
    """Open the prebuilt vector database (phase 1 output)."""
    if index_exists(persist_directory):
        vectorstore = Chroma(
            persist_directory=persist_directory,
            embedding_function=embeddings
        )
        print(f"Vector database loaded from {persist_directory}.")
        return vectorstore

    if not ALLOW_RUNTIME_BUILD:
        raise RuntimeError(
            f"No vector database at {persist_directory}. "
            "It must be built at deployment time (see build_index.py)."
        )

    print(f"[WARN] No vector database at {persist_directory}; building it now. "
          "This should have happened at build time.")
    return build_index(embeddings, persist_directory=persist_directory)


# ========================
# Phase 2 - serving resources
# ========================

def _is_noise_doc(doc) -> bool:
    """Heads, running heads, tables of contents, bibliography/index lines and
    JSTOR-style download watermarks pollute the top-k for short queries like
    "where is the battle of adwa?", so drop them cheaply before they reach
    the LLM."""
    text = re.sub(r"\s+", " ", doc.page_content or "").strip()
    if len(text) < 40:
        return True
    if "content downloaded from" in text:
        return True
    numbers = re.findall(r"\b\d{1,4}\b", text)
    if len(numbers) >= 3 and len(text) < 400:
        return True
    return False


def select_relevant_docs(docs, k=TOP_K):
    """Filter retrieval noise, then trim to the final k."""

    kept = [doc for doc in docs if not _is_noise_doc(doc)]
    return (kept or docs)[:k]


def build_resources():
    """Build everything a request needs: retriever + RAG chain."""
    groq_api_key = os.getenv("GROQ_API_KEY")

    if not groq_api_key:
        raise RuntimeError("GROQ_API_KEY is not set")

    embeddings = load_embeddings()
    vectorstore = load_vectorstore(embeddings)

    retriever = vectorstore.as_retriever(
        search_kwargs={"k": RETRIEVE_CANDIDATES}
    )

    llm = ChatGroq(
        model_name=LLM_MODEL,
        groq_api_key=groq_api_key,
        timeout=LLM_TIMEOUT_SECONDS,
        max_retries=LLM_MAX_RETRIES
    )

    prompt_template = ChatPromptTemplate.from_template(prompt)
    document_chain = create_stuff_documents_chain(llm, prompt_template)

    def run(inputs):
        question = inputs["question"]
        docs = select_relevant_docs(retriever.invoke(question), TOP_K)
        answer = document_chain.invoke({"context": docs, "question": question})
        return {"answer": answer, "context": docs}

    rag_chain = RunnableLambda(run)

    return {
        "retriever": retriever,
        "rag_chain": rag_chain,
    }
