#!/usr/bin/env python3
import hashlib
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import jwt


def main() -> int:
    secret = os.environ.get("TIGER_PAY_CLIENT_SECRET", "").strip()
    if not secret:
        print("TIGER_PAY_CLIENT_SECRET is required", file=sys.stderr)
        return 1

    base_url = os.environ.get(
        "TIGER_PAY_WEBHOOK_TEST_URL",
        "http://127.0.0.1:8000/webhooks/tiger-pay",
    ).rstrip("/")

    payload = {
        "payment": {
            "id": 9001,
            "type": "Cash",
            "paymentNo": "PAY-DEV-9001",
            "status": "Paid",
            "amount": "99.00",
            "totalPay": "99.00",
            "createdAt": "2026-07-13T10:00:00",
            "updatedAt": "2026-07-13T10:00:05",
        },
        "shop": {
            "name": "DEV01",
            "shopName": "Dev Shop",
            "branchName": "Bangkok",
        },
    }

    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    body_sha256 = hashlib.sha256(body).hexdigest()
    token = jwt.encode({"messageDigest": body_sha256}, secret, algorithm="HS256")

    request = Request(
        base_url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urlopen(request, timeout=30) as response:
            response_body = response.read().decode("utf-8")
            print(response.status)
            print(response_body)
    except HTTPError as exc:
        response_body = exc.read().decode("utf-8")
        print(exc.code)
        print(response_body)
    except URLError as exc:
        print(f"request failed: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
