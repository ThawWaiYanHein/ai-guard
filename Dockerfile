FROM python:3.11-slim

ARG AI_GUARD_VERSION=0.1.0

ENV PYTHONUNBUFFERED=1 \
    AI_GUARD_VERSION=${AI_GUARD_VERSION}

WORKDIR /ai-guard

COPY requirements.txt /ai-guard/requirements.txt
RUN pip install --no-cache-dir -r /ai-guard/requirements.txt

COPY agent /ai-guard/agent
COPY operator /ai-guard/operator

RUN adduser --disabled-password --gecos "" --uid 65532 ai-guard
USER 65532:65532

EXPOSE 8443
CMD ["python", "/ai-guard/operator/webhook.py"]
