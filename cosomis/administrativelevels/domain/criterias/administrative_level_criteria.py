from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AdministrativeLevelCriteria:
    id: Optional[int] = None
    type: Optional[str] = None
    name: Optional[str] = None