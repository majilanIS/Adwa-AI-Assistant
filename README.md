# Adwa AI - The Battle of Adwa, explained by AI

**Adwa AI** is a RAG-powered assistant that answers questions about the Battle of Adwa (March 1, 1896) and Ethiopian history, grounded only in a curated source library - never in what the model "remembers".

This project is being built for the **Addis Ababa University Hackathon**, showcasing how a small team can ship a production-ready, source-grounded AI experience with a React frontend, a Python + LangChain RAG backend, and a fully automated Docker / CI-CD pipeline.

---

## Features

- **Source-grounded answers** - Retrieval over a curated library of books, papers and historical notes (ChromaDB). Every answer reports which document it came from.
- **Two-phase RAG pipeline** - Index the library once at build time (`build_index.py`), then serve queries with zero per-request embedding cost.
- **Historian-style output** - Structured `Title / Summary / Details / Key Facts` answers, with out-of-scope and "not in source" responses handled in the prompt.
- **Text and voice input** - Ask through a polished, responsive UI.
- **Fully automated** - Multi-stage Docker image, GitHub Actions CI/CD, with the vector database baked into the shipped image.
- **Large source library** - 767+ pages of source material (PDFs + notes) split into 3,200+ searchable chunks.

---

## Tech Stack

| Layer     | Tech                                                        |
| :-------- | :---------------------------------------------------------- |
| Frontend  | React 19, Vite, Axios                                       |
| Backend   | Flask, Gunicorn, LangChain                                  |
| Retrieval | ChromaDB, sentence-transformers (`all-MiniLM-L6-v2`)        |
| LLM       | Groq (`openai/gpt-oss-20b`) via `langchain-groq`            |
| Infra     | Docker, Docker Compose, GitHub Actions (CI + CD to GHCR)    |

---

## Project Structure

```
├── backend/            Flask RAG API
│   ├── app.py          Serving layer (chat, voice, health)
│   ├── build_index.py  Vector DB creation (pre-build / phase 1)
│   ├── build_index.sh  Shared pre-build command (Docker + CI)
│   ├── rag.py          Retrieval chain, Chroma, embeddings
│   ├── prompt.py       Historian-style system prompt
│   └── data/           Source library (PDFs and notes)
├── frontend/           React + Vite UI
├── docker-compose.yml  Local orchestration
└── .github/workflows/  CI and CD pipelines
```

---

## Getting Started

### Prerequisites

- Python 3.11, Node 20+, Docker (for the container path)
- A Groq API key from https://console.groq.com/keys

### 1) Configure environment

Create `backend/.env`:

```bash
GROQ_API_KEY=gsk_xxxxxxxx
ENV=PRODUCTION
```

### 2) Run with Docker (recommended)

The vector database is built at image build time, so the first build is slow (downloads PyTorch and embeds the library) but every run after is instant:

```bash
docker compose up -d --build
```

Backend: http://localhost:10000 - Frontend: http://localhost:5173

### 3) Run locally (dev mode)

Backend:

```bash
cd backend
python -m venv venv && venv\Scripts\activate   # Windows
source venv/bin/activate                       # macOS/Linux
pip install -r requirements.txt
python build_index.py                          # Phase 1 - create vector DB (one-time)
python app.py                                  # Phase 2 - serve on :10000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

---

## API Endpoints

| Method | Endpoint   | Description                                    |
| :----- | :--------- | :--------------------------------------------- |
| GET    | `/health`  | Liveness check                                 |
| GET    | `/ready`   | Readiness (index loaded and warm)              |
| POST   | `/chat`    | Ask a question (answer + sources)              |
| POST   | `/voice`   | Answer from transcribed voice text             |
| POST   | `/new-chat`| Reset conversation                             |
| GET    | `/history` | Current conversation history                   |

Example:

```bash
curl -X POST https://localhost:10000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Who led the Ethiopian army at Adwa?"}'
```

---

## CI/CD

- **CI** - Lints and builds the frontend, syntax-checks the backend, and builds the Docker image on every push.
- **CD** - Pushes the built image to GHCR, ready to deploy to Render or any container host.

---

## Hackathon

Built for the **Addis Ababa University Hackathon** - demonstrating how an Ethiopian historical heritage experience can be powered by responsible, source-grounded generative AI.