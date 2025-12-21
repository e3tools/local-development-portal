from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class InvestmentCriteria:
    id: Optional[str] = None
    administrative_level_id: Optional[int] = None