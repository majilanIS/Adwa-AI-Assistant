import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from prompt import prompt


# ========================
# Flask Setup
# ========================
app = Flask(__name__)
CORS(app)

# ========================
# Load Environment
# ========================
load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")

if not groq_api_key:
    raise ValueError("GROQ_API_KEY not found in .env")

# ========================
# Embeddings & Vector DB
# ========================
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

persist_directory = "./adwa_db"

if os.path.exists(persist_directory) and os.listdir(persist_directory):

    vectorstore = Chroma(
        persist_directory=persist_directory,
        embedding_function=embeddings
    )

    print("Vector database loaded.")

else:

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
            f"Document-{i+1}"
        )

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=persist_directory
    )

    print("Vector database created.")

# ========================
# Retriever & LLM
# ========================
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

# ========================
# Conversation Memory
# ========================
conversation = []

# ========================
# Routes
# ========================

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Adwa AI Backend Running"})


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

    data = request.get_json()
    message = data.get("message")

    if not message:
        return jsonify({"error": "Message is required"}), 400

    try:
        # Retrieve documents
        try:
            docs = retriever.get_relevant_documents(message)
        except:
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

        except:
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
            "response": answer,
            "sources": sources
        })

    except Exception:
        return jsonify({
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

    try:

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
