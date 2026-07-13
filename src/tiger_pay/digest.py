import hashlib


def compute_body_sha256(raw_body: bytes) -> str:
    # Tiger Pay's Node.js example hashes the raw HTTP body with plain SHA-256,
    # not HMAC-SHA256, despite ambiguous written documentation.
    return hashlib.sha256(raw_body).hexdigest()
