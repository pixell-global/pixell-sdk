class AgentUISpecError(Exception):
    pass


class AgentUIValidationError(AgentUISpecError):
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.details = details or {}


class AgentUICapabilityError(AgentUISpecError):
    pass
