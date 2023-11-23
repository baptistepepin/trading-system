# standard
# TODO review this
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict


class Venue(int, Enum):
    ALPACA = 1
    # Add other venues as needed


VenueMap: Dict[str, Venue] = {
    'alpaca': Venue.ALPACA,
    # Add other venues as needed
}


class StrategyType(int, Enum):
    SMA = 1
    # Add other strategies as needed


StrategyTypeMap: Dict[str, StrategyType] = {
    'sma': StrategyType.SMA,
    # Add other strategy types as needed
}


class Exposure(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class Quote:
    def __init__(self, venue: Venue, symbol: str, timestamp: datetime):
        self.venue = venue
        self.symbol = symbol
        self.bid_prc: Optional[float] = None
        self.ask_prc: Optional[float] = None
        self.bid_qty: Optional[float] = None
        self.ask_qty: Optional[float] = None
        self.timestamp = timestamp

    def __repr__(self):
        return f"Quote (venue={self.venue}, symbol={self.symbol}, bid={self.bid_qty}@{self.bid_prc}, ask={self.ask_qty}@{self.ask_prc}, ts={self.timestamp})"


class Trade:
    def __init__(self, venue: Venue, symbol: str, timestamp: datetime):
        self.venue = venue
        self.symbol = symbol
        self.price: Optional[float] = None
        self.volume: Optional[float] = None
        self.id: Optional[int] = None
        self.timestamp = timestamp

    def __repr__(self):
        return f"Trade (venue={self.venue}, symbol={self.symbol}, price={self.price}, volume={self.volume}, ts={self.timestamp})"


class Signal:
    def __init__(self, venue: Venue, symbol: str, exposure: Exposure, qty: float, prc: float):
        self.venue = venue
        self.symbol = symbol
        self.exposure = exposure
        self.qty = qty
        self.prc = prc

    def __repr__(self):
        return f"Signal (venue={self.venue}, symbol={self.symbol}, exposure={self.exposure}, qty={self.qty}, prc={self.prc})"