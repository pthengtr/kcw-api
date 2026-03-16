from dataclasses import dataclass, field
from typing import Any


@dataclass
class SearchQuery:
    raw: str
    limit: int = 20
    min_term_len: int = 2
    terms: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.raw = (self.raw or "").strip()
        self.terms = self._split_terms(self.raw)

    def _split_terms(self, text: str) -> list[str]:
        if not text:
            return []
        terms = [x.strip() for x in text.split() if x.strip()]
        return [x for x in terms if len(x) >= self.min_term_len]

    @property
    def is_empty(self) -> bool:
        return not self.raw

    @property
    def term_count(self) -> int:
        return len(self.terms)

    def to_sql_params(self) -> dict[str, Any]:
        params: dict[str, Any] = {
            "q": self.raw,
            "q_exact": self.raw,
            "q_prefix": f"{self.raw}%",
            "q_like": f"%{self.raw}%",
            "limit": self.limit,
        }

        for i, term in enumerate(self.terms):
            params[f"term_exact_{i}"] = term
            params[f"term_prefix_{i}"] = f"{term}%"
            params[f"term_like_{i}"] = f"%{term}%"

        return params