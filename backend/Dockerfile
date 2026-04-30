FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DEFAULT_TIMEOUT=100
ENV PIP_RETRIES=20

WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip setuptools wheel
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
RUN pip install --no-cache-dir /tmp/torch-2.11.0+cpu-cp311-cp311-manylinux_2_28_x86_64.whl
RUN pip install --no-cache-dir --retries 20 --default-timeout 100 -r /app/requirements.txt
RUN pip install --no-cache-dir --retries 20 --default-timeout 100 gunicorn

# Copy application code
COPY . /app

EXPOSE 10000

CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-10000} app:app"]
