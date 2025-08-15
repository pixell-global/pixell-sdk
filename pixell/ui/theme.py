from typing import Any, Dict
from pydantic import BaseModel, Field


class Theme(BaseModel):
    tokens: Dict[str, Any] = Field(default_factory=dict) 