# 🇪🇹 Adwa AI – The Battle of Adwa, explained by AI

**Adwa AI** is a RAG-powered assistant that answers questions about the Battle of Adwa (March 1, 1896) and Ethiopian history — grounded only in a curated source library, never in what the model "remembers".

Built for the **Ethiopian Hackathon** 🇪🇹, this project shows how a small team can ship a production-ready, source-grounded AI experience: a React frontend, a Python + LangChain RAG backend, and a fully automated Docker/CI-CD pipeline.

## ✨ Features

- **Source-grounded answers** – Vector search over real books, papers & historical notes (ChromaDB). Every answer cites which document it came from.
- **RAG done right** – Two-phase pipeline: index the library *once* at build time (`build_index.py`), then serve fast queries with zero per-request embedding cost.
- **Structured historian output** – `Title / Summary / Details / Key Facts`, with strict out-of-scope and "not in source" handling baked into the prompt.
- **Voice support** – Ask by voice and text from a polished, responsive UI.
- **Automated everything** – Docker multi-stage image, GitHub Actions CI/CD, the vector DB is baked into the shipped image.
- **Handles 767+ pages** of source material (PDFs + notes) split into 3,200+ searchable chunks.

## 🧱 Tech Stack

| Layer | Tech |
| :--- | :--- |
| Frontend | React 19, Vite, Axios |
| Backend | Flask, Gunicorn, LangChain |
| Retrieval | ChromaDB, sentence-transformers (`all-MiniLM-L6-v2`) |
| LLM | Groq (`openai/gpt-oss-20b`) via `langchain-groq` |
| Infra | Docker, Docker Compose, GitHub Actions (CI + CD to GHCR), Render |

## 🗂️ Project Structure

```
├── backend/            # Flask RAG API
│   ├── app.py          # Phase 2 - serving (chat, voice, health)
│   ├── build_index.py  # Phase 1 - vector DB creation (pre-build)
│   ├── build_index.sh  # Shared pre-build command (Docker + CI)
│   ├── rag.py          # Retrieval chain, Chroma, embeddings
│   ├── prompt.py       # Historian-style system prompt
│   └── data/           # Source library (PDFs, notes)
├── frontend/           # React + Vite UI
├── docker-compose.yml  # Local orchestration
└── .github/workflows/  # CI + CD pipelines
```

## 🚀 Getting Started

### Prerequisites

- **Python 3.11**, **Node 20+**, **Docker** (for the container path)
- A **Groq API key** → https://console.groq.com/keys

### 1) Environment setup

```bash
# backend/.env
GROQ_API_KEY=gsk_xxxxxxxx
ENV=PRODUCTION
```

### 2) Run with Docker (recommended)

The image builds the vector DB **at build time**, so the first build is slow (downloads PyTorch + embeds the library) but every run after is instant:

```bash
docker compose up -d --build
# Backend → http://localhost:10000  |  Frontend → http://localhost:5173
```

### 3) Run locally (dev mode)

**Backend**

```bash
cd backend
python -m venv venv && venv\Scripts\activate   # Windows
source venv/bin/activate                       # macOS/Linux
pip install -r requirements.txt
python build_index.py                          # Phase 1: create vector DB (one-time)
python app.py                                  # Phase 2: serve on :10000
```

**Frontend**

```bash
cd frontend
npm install
npm run dev        # serves on :5173, points to VITE_API_URL
```

## 🔌 API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Liveness check |
| `GET` | `/ready` | Readiness (index loaded & warm) |
| `POST` | `/chat` | Ask a question (returns answer + sources) |
| `POST` | `/voice` | Answer from transcribed voice text |
| `POST` | `/new-chat` | Reset conversation |
| `GET` | `/history` | Current conversation history |

Example:

```bash
curl -X POST http://localhost:10000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Who led the Ethiopian army at Adwa?"}'
```

## 🔁 CI/CD

- **CI** – lints/builds the frontend, syntax-checks the backend, and builds the Docker image on every push.
- **CD** – pushes the built image to **GHCR** and can be deployed to Render/Hosting with one click.

## 🏆 Hackathon

This project is being built to participate in the **Ethiopian Hackathon** 🇪🇹 — demonstrating how an Ethiopian historical heritage experience can be powered by responsible, source-grounded generative AI.