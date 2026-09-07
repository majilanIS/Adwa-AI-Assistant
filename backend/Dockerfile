# syntax=docker/dockerfile:1

# =============================================================================
# Stage 1 - builder
#
# Installs dependencies and runs phase 1 of the RAG pipeline:
#   load PDFs -> split into chunks -> embed chunks -> persist Chroma DB
# Build tooling, pip caches and the torch wheel stay in this stage and never
# reach the shipped image.
# =============================================================================
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DEFAULT_TIMEOUT=100
ENV PIP_RETRIES=20

WORKDIR /app

# Packages go into the image's system site-packages rather than a venv; the
# runtime stage copies /usr/local wholesale. A venv under /opt is the usual
# alternative but trips a read-only-layer bug in some BuildKit snapshotters.
RUN pip install --upgrade pip setuptools wheel

# The CPU-only torch wheel is large and the download is the least reliable step
# of the build, so it is fetched with resumable ranged retries rather than by
# pip alone.
RUN python - <<'PY'
import os
import time
import urllib.request

url = "https://download.pytorch.org/whl/cpu/torch-2.11.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl"
target = "/tmp/torch-2.11.0+cpu-cp311-cp311-manylinux_2_28_x86_64.whl"
headers = {}

for attempt in range(1, 8):
	mode = "ab" if os.path.exists(target) else "wb"
	start = os.path.getsize(target) if os.path.exists(target) else 0
	if start:
		headers["Range"] = f"bytes={start}-"
	request = urllib.request.Request(url, headers=headers)
	try:
		with urllib.request.urlopen(request, timeout=120) as response, open(target, mode) as file_handle:
			while True:
				chunk = response.read(1024 * 1024)
				if not chunk:
					break
				file_handle.write(chunk)
		break
	except Exception as error:
		if attempt == 7:
			raise
		print(f"torch download attempt {attempt} failed: {error}")
		time.sleep(5)

PY

# Installing torch first stops sentence-transformers from pulling the much
# larger default (CUDA) build as a transitive dependency.
RUN pip install --no-cache-dir /tmp/torch-2.11.0+cpu-cp311-cp311-manylinux_2_28_x86_64.whl

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# ========================
# Phase 1 - one-time initialization
# ========================
ENV DATA_DIR=/app/data
ENV VECTOR_DB_DIR=/app/adwa_db_v2
ENV EMBEDDING_MODEL_DIR=/app/models/all-MiniLM-L6-v2
ENV HF_HOME=/tmp/hf

# Only the files phase 1 actually reads are copied here, so editing app.py does
# not invalidate this layer and force the PDFs to be re-embedded.
COPY prompt.py rag.py build_index.py /app/
COPY data /app/data

RUN python build_index.py && rm -rf /tmp/hf


# =============================================================================
# Stage 2 - runtime
#
# Phase 2 only: embed query -> similarity search -> prompt -> LLM -> response.
# The vector database and embedding model arrive prebuilt from the builder, so
# no request ever pays for document loading, embedding or a model download.
# =============================================================================
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN useradd --create-home --uid 10001 adwa

WORKDIR /app

# Installed packages plus console scripts (gunicorn). Both stages share the
# same python:3.11-slim base, so /usr/local transfers cleanly.
COPY --from=builder /usr/local /usr/local

COPY --chown=adwa:adwa . /app

# Phase 1 output. Chroma opens its SQLite file read-write even for queries, so
# these must be owned by the runtime user.
COPY --from=builder --chown=adwa:adwa /app/adwa_db_v2 /app/adwa_db_v2
COPY --from=builder --chown=adwa:adwa /app/models /app/models

ENV DATA_DIR=/app/data
ENV VECTOR_DB_DIR=/app/adwa_db_v2
ENV EMBEDDING_MODEL_DIR=/app/models/all-MiniLM-L6-v2

# The index ships with the image, so a missing one is a deployment bug - fail
# loudly instead of rebuilding it inside a user request.
ENV ALLOW_RUNTIME_INDEX_BUILD=0
ENV ENV=production
ENV PORT=10000

USER adwa

EXPOSE 10000

# /health answers immediately and never touches the model, so a slow warmup
# does not look like a dead container.
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
	CMD python -c "import os,urllib.request;urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','10000')+'/health',timeout=4)"

# One worker keeps a single copy of the embedding model in memory; threads
# handle concurrent requests. The timeout covers the slowest Groq call.
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT:-10000} --workers ${WEB_CONCURRENCY:-1} --threads ${WEB_THREADS:-8} --timeout ${WEB_TIMEOUT:-120} --graceful-timeout 30 --access-logfile - --error-logfile - app:app"]
