from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Action:
    type: str
    value: str
    label: str


@dataclass
class BotResponse:
    text: str
    actions: Optional[List[Action]] = None