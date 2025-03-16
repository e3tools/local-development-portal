from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class InvestmentCriteria:
    administrative_level: Optional[int] = None