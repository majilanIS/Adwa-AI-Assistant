"""
Phase 2 of the RAG pipeline - runs on every user message.

    5. User sends query
    6. Embed query (same MiniLM model)
    7. Similarity search (top-k chunks)
    8. Build prompt (system prompt + context + query)
    9. Groq LLM generates the answer
   10. JSON response returned to the client

Phase 1 (documents -> chunks -> embeddings -> Chroma) is done at build time by
build_index.py, so nothing here loads PDFs or embeds documents.
"""

import os
import threading
import time
import traceback

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

import rag

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

if not os.getenv("GROQ_API_KEY"):
    raise RuntimeError("GROQ_API_KEY is not set")

# How long a request may wait for warmup before giving up with 503.
# Kept well under the client timeout so the caller gets a real answer, not a
# hung socket.
WARMUP_WAIT_SECONDS = float(os.getenv("WARMUP_WAIT_SECONDS", "20"))

_resources = None
_resources_error = None
_ready_event = threading.Event()
_warmup_lock = threading.Lock()
_warmup_started = False


def _warmup():
    """Load the prebuilt index and build the chain. Runs once per process."""
    global _resources
    global _resources_error

    started = time.time()

    try:
        _resources = rag.build_resources()
        print(f"AI resources ready in {time.time() - started:.1f}s")
    except Exception as error:
        _resources_error = error
        print("[ERROR] Failed to initialize AI resources:", error)
        traceback.print_exc()
    finally:
        _ready_event.set()


def start_warmup():
    """Kick off warmup in the background, at most once."""
    global _warmup_started

    with _warmup_lock:
        if _warmup_started:
            return
        _warmup_started = True

    threading.Thread(target=_warmup, daemon=True, name="warmup").start()


def get_resources(wait_seconds=WARMUP_WAIT_SECONDS):
    """Return the serving resources, waiting a bounded time for warmup.

    Raises RuntimeError if warmup failed, TimeoutError if it is still running.
    """
    start_warmup()

    if not _ready_event.wait(timeout=wait_seconds):
        raise TimeoutError("AI resources are still loading")

    if _resources_error is not None:
        raise RuntimeError("AI resources failed to load") from _resources_error

    return _resources


def _not_ready_response(error, payload_key="error"):
    if isinstance(error, TimeoutError):
        message = "AI resources are still loading. Please try again in a moment."
    else:
        message = "AI service is unavailable. Please try again later."

    body = {"success": False, payload_key: message, "ready": False, "retry_after": 5}
    response = jsonify(body)
    response.headers["Retry-After"] = "5"
    return response, 503


def _status():
    if _resources is not None:
        return "ready"
    if _resources_error is not None:
        return "failed"
    return "loading"


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
        "status": _status(),
    })


# Liveness - always instant, never touches the model.
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


# Readiness - tells the client whether phase 2 can serve yet.
@app.route("/ready", methods=["GET"])
def ready():
    start_warmup()
    status = _status()
    return jsonify({
        "ready": status == "ready",
        "status": status,
    }), (200 if status == "ready" else 503)


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

    data = request.get_json(silent=True) or {}
    message = data.get("message")

    if not message:
        return jsonify({"success": False, "error": "Message is required"}), 400

    try:
        resources = get_resources()
    except (TimeoutError, RuntimeError) as error:
        return _not_ready_response(error)

    try:
        rag_chain = resources["rag_chain"]

        # Steps 6-9. The chain retrieves internally and returns the documents
        # it used, so the query is embedded and searched exactly once.
        result = rag_chain.invoke({
            "input": message,
            "question": message,
        })

        answer = result.get("answer")
        docs = result.get("context") or []

        sources = sorted({
            doc.metadata.get("source", "Unknown")
            for doc in docs
        })

        # Out-of-scope protection
        if not answer or answer.strip().lower() in ["none", "none."]:
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

    data = request.get_json(silent=True) or {}
    text = data.get("text")

    if not text:
        return jsonify({"error": "Text is required"}), 400

    try:
        resources = get_resources()
    except (TimeoutError, RuntimeError) as error:
        return _not_ready_response(error)

    try:
        result = resources["rag_chain"].invoke({
            "input": text,
            "question": text,
        })

        return jsonify({
            "response": result.get("answer")
        })

    except Exception as e:
        print("[ERROR] /voice endpoint failed:", e)
        traceback.print_exc()
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

# Warm up as soon as the process starts, under gunicorn as well as locally,
# so the first user message does not pay the loading cost.
start_warmup()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
