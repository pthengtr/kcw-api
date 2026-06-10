import os

from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_TIMEOUT_SECONDS = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "12").strip())

_client: OpenAI | None = None


def get_openai_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=OPENAI_API_KEY,
            max_retries=0,
        )
    return _client


def extract_text_from_response(resp) -> str:
    output_text = getattr(resp, "output_text", None)
    if output_text:
        return str(output_text).strip()

    parts: list[str] = []
    for item in getattr(resp, "output", None) or []:
        for content in getattr(item, "content", None) or []:
            text = getattr(content, "text", None)
            if text:
                parts.append(str(text))

    return "\n".join(parts).strip()


def extract_usage_from_response(resp) -> dict[str, int]:
    usage = getattr(resp, "usage", None)
    if not usage:
        return {}

    def _as_int(value) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    if isinstance(usage, dict):
        input_tokens = _as_int(usage.get("input_tokens"))
        output_tokens = _as_int(usage.get("output_tokens"))
        total_tokens = _as_int(usage.get("total_tokens"))
    else:
        input_tokens = _as_int(getattr(usage, "input_tokens", 0))
        output_tokens = _as_int(getattr(usage, "output_tokens", 0))
        total_tokens = _as_int(getattr(usage, "total_tokens", 0))

    if not total_tokens:
        total_tokens = input_tokens + output_tokens

    if not any((input_tokens, output_tokens, total_tokens)):
        return {}

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
    }
