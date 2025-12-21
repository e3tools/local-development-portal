from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PackageCriteria:
    id: Optional[str] = None
    user_id: Optional[int] = None
    status: Optional[str] = None