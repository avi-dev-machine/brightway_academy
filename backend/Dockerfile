FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Unicode fonts so receipts and ID cards can render non-Latin names.
    PDF_FONT_PATH=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf \
    PDF_FONT_BOLD_PATH=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf

RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
COPY scripts ./scripts

RUN useradd --create-home --uid 10001 brightway
USER brightway

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD python -c "import sys, urllib.request; sys.exit(urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).status != 200)"

# Behind a reverse proxy set FORWARDED_ALLOW_IPS to the proxy address so client IPs
# (used for rate limiting) are taken from X-Forwarded-For only when it is trustworthy.
# The scheduler runs from the same image: `python -m app.workers.scheduler`.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
