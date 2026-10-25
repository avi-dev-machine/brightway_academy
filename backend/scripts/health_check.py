"""Probe a running backend's health endpoints. Exit code 0 only if all are healthy.

python -m scripts.health_check [--url http://localhost:8000]
"""

import argparse
import sys

import httpx


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Brightway health check")
    parser.add_argument("--url", default="http://localhost:8000")
    args = parser.parse_args(argv)

    healthy = True
    for path in ("/health", "/health/db", "/health/storage"):
        try:
            response = httpx.get(f"{args.url.rstrip('/')}{path}", timeout=10)
            ok = response.status_code == 200
            detail = response.json().get("data") if ok else response.text[:200]
        except httpx.HTTPError as exc:
            ok, detail = False, f"{type(exc).__name__}: {exc}"
        healthy &= ok
        print(f"{'OK  ' if ok else 'FAIL'} {path} {detail}")
    return 0 if healthy else 1


if __name__ == "__main__":
    sys.exit(main())
