"""This module contains entity-definitions that constitute the data and state of MarketDataService"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Set

BASE_CURRENCY = "USD"


@dataclass(frozen=False)
class Security:
    """
    Security represents a market data series.
    It consists of symbol, its native currency, and latest price, if available
    This class is mutable as the price may keep changing.
    """
    symbol: str
    currency: str
    price: Optional[float] = field(default=None)


@dataclass(frozen=True, eq=True)
class Subscription:
    """
    Subscription represents a unique subscription request.
    It consists of a user, symbol, and currency.
    This class is immutable (hence hashable), and is intended to be used as lookup key
    """
    user: str
    symbol: str
    currency: str


@dataclass(frozen=False)
class Config:
    """
    Config models initial config provided in terms of symbols, their currencies, and user entitlements.
    Additionally, it defines a base currency which is used to express all currency exchange rates.
    """
    securities: Dict[str, Security]
    entitlements: Dict[str, Set[str]]
    base_currency: str = field(default=BASE_CURRENCY)
