import os
import shutil
import threading
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from prompt import prompt
from sentence_transformers import SentenceTransformer

# ========================
# Flask Setup
# ========================
app = Flask(__name__)
CORS(app)

# ========================
# Load Environment
# ========================
if os.getenv("ENV") != "production":
    load_dotenv()

groq_api_key = os.getenv("GROQ_API_KEY")

if not groq_api_key:
    raise RuntimeError("GROQ_API_KEY is not set")

_resources_lock = threading.Lock()
_resources = None
_resources_error = None


class SentenceTransformerEmbeddings:

    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self._model = SentenceTransformer(model_name)

    def embed_documents(self, texts):
        return self._model.encode(
            texts,
            convert_to_tensor=False,
            normalize_embeddings=True
        ).tolist()

    def embed_query(self, text):
        return self._model.encode(
            [text],
            convert_to_tensor=False,
            normalize_embeddings=True
        )[0].tolist()


def _build_vectorstore(embeddings, persist_directory):
    if os.path.exists(persist_directory) and os.listdir(persist_directory):
        try:
            vectorstore = Chroma(
                persist_directory=persist_directory,
                embedding_function=embeddings
            )
            print("Vector database loaded.")
            return vectorstore
        except Exception as error:
            print("[WARN] Existing vector database is incompatible, rebuilding:", error)
            shutil.rmtree(persist_directory, ignore_errors=True)

    print("Creating new vector database...")

    loader = PyPDFDirectoryLoader(path="./data", glob="*.pdf")
    documents = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=200
    )

    chunks = splitter.split_documents(documents)

    for i, doc in enumerate(chunks):
        doc.metadata["source"] = doc.metadata.get(
            "source",
            f"Document-{i + 1}"
        )

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=persist_directory
    )

    print("Vector database created.")
    return vectorstore

def get_resources():
    global _resources
    global _resources_error

    if _resources is not None:
        return _resources

    if _resources_error is not None:
        raise _resources_error

    with _resources_lock:
        if _resources is not None:
            return _resources

        if _resources_error is not None:
            raise _resources_error

        try:
            embeddings = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
            persist_directory = "./adwa_db_v2"

            vectorstore = _build_vectorstore(embeddings, persist_directory)

            retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

            llm = ChatGroq(
                model_name="llama-3.1-8b-instant",
                groq_api_key=groq_api_key
            )

            prompt_template = ChatPromptTemplate.from_template(prompt)

            document_chain = create_stuff_documents_chain(
                llm,
                prompt_template
            )

            rag_chain = create_retrieval_chain(
                retriever,
                document_chain
            )

            _resources = {
                "retriever": retriever,
                "rag_chain": rag_chain,
            }

            return _resources

        except Exception as error:
            _resources_error = error
            print("[ERROR] Failed to initialize AI resources:", error)
            raise

# ========================
# Conversation Memory
# ========================
conversation = []

# ========================
# Routes
# ========================

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Adwa AI Backend Running",
        "ready": _resources is not None,
    })


# Start new chat
@app.route("/new-chat", methods=["POST"])
def new_chat():

    global conversation
    conversation = []

    return jsonify({"message": "New chat started"})


# ========================
# TEXT CHAT ENDPOINT
# ========================

@app.route("/chat", methods=["POST"])
def chat():

    import traceback
    data = request.get_json()
    message = data.get("message")

    if not message:
        return jsonify({"success": False, "error": "Message is required"}), 400

    if _resources is None:
        try:
            get_resources()
        except Exception:
            return jsonify({
                "success": False,
                "error": "AI resources are still loading. Please try again in a moment."
            }), 503

        if _resources is None:
            return jsonify({
                "success": False,
                "error": "AI resources are still loading. Please try again in a moment."
            }), 503

    try:
        resources = get_resources()
        retriever = resources["retriever"]
        rag_chain = resources["rag_chain"]

        # Retrieve documents
        try:
            docs = retriever.invoke(message)
        except Exception as e:
            print("[ERROR] Document retrieval failed:", e)
            traceback.print_exc()
            docs = []

        sources = list(set([
            doc.metadata.get("source", "Unknown")
            for doc in docs
        ]))

        # Run RAG
        try:
            result = rag_chain.invoke({
                "input": message,
                "question": message,
            })
            answer = result.get("answer")
        except Exception as e:
            print("[ERROR] RAG chain failed:", e)
            traceback.print_exc()
            answer = "I could not generate an answer."

        # Out-of-scope protection
        if not answer or answer.lower() in ["none", "none."]:
            answer = "I'm sorry, I can only answer questions about the Battle of Adwa and Ethiopian history."
            sources = []

        # Save conversation
        conversation.append({
            "role": "user",
            "message": message
        })

        conversation.append({
            "role": "ai",
            "message": answer,
            "sources": sources
        })

        return jsonify({
            "success": True,
            "response": answer,
            "sources": sources
        })

    except Exception as e:
        print("[ERROR] /chat endpoint failed:", e)
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": "Server error"
        }), 500


# ========================
# VOICE ENDPOINT
# ========================

@app.route("/voice", methods=["POST"])
def voice():

    data = request.get_json()

    text = data.get("text")

    if not text:
        return jsonify({"error": "Text is required"}), 400

    if _resources is None:
        try:
            get_resources()
        except Exception:
            return jsonify({
                "error": "AI resources are still loading. Please try again in a moment."
            }), 503

        if _resources is None:
            return jsonify({
                "error": "AI resources are still loading. Please try again in a moment."
            }), 503

    try:
        resources = get_resources()
        rag_chain = resources["rag_chain"]
        result = rag_chain.invoke({
            "input": text,
            "question": text,
        })

        answer = result.get("answer")

        return jsonify({
            "response": answer
        })

    except Exception:
        return jsonify({
            "error": "Voice processing failed"
        }), 500


# ========================
# Conversation History
# ========================

@app.route("/history", methods=["GET"])
def get_history():

    return jsonify({
        "conversation": conversation
    })


# ========================
# Run Server
# ========================

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )

else:
    warmup_thread = threading.Thread(target=lambda: get_resources(), daemon=True)
    warmup_thread.start()
