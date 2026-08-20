# Hugging Face Spaces serves on port 7860 and runs as a non-root user.
FROM python:3.13-slim

# Running on Linux is the point: agent/sandbox.py's RLIMIT_AS / RLIMIT_CPU /
# RLIMIT_NPROC ceilings only exist on POSIX, so they are inert on Windows and
# active here. tests/test_sandbox_posix.py can finally run in this image.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOME=/home/appuser

RUN useradd -m -u 1000 appuser
WORKDIR /app

COPY serve/requirements.txt /app/serve/requirements.txt
RUN pip install --no-cache-dir -r /app/serve/requirements.txt

COPY agent/ /app/agent/
COPY problems/ /app/problems/
COPY serve/ /app/serve/

USER appuser
EXPOSE 7860

# Shell form so ${PORT} expands: Render assigns the port at runtime, while
# local runs and other hosts fall back to 7860.
CMD uvicorn serve.app:app --host 0.0.0.0 --port ${PORT:-7860} --workers 1
