from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RequiredWhen:
    field_name: str
    equals: Any