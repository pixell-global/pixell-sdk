from typing import Set


class IntentPolicy:
    def __init__(self, allowed: Set[str] | None = None):
        self.allowed: Set[str] = set(allowed or [])

    def is_allowed(self, intent: str) -> bool:
        return not self.allowed or intent in self.allowed 