# standard
from enum import Enum
from datetime import datetime
from typing import Optional, Dict

from alpaca.trading import OrderSide


class Venue(int, Enum):
    ALPACA = 1
    # Add other venues as needed


VenueMap: Dict[str, Venue] = {
    "alpaca": Venue.ALPACA,
    # Add other venues as needed
}


class StrategyType(int, Enum):
    SMA = 1
    RSI = 2
    Strat1 = 3
    # Add other strategies as needed


StrategyTypeMap: Dict[str, StrategyType] = {
    "sma": StrategyType.SMA,
    "rsi": StrategyType.RSI,
    "strat1": StrategyType.Strat1,
    # Add other strategy types as needed
}


class Exposure(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


ExposureToSideMap: Dict[Exposure, OrderSide] = {
    Exposure.LONG: OrderSide.BUY,
    Exposure.SHORT: OrderSide.SELL,
}


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
        return """Quote (
            venue={venue},
            symbol={symbol},
            bid={bid_qty}@{bid_prc},
            ask={ask_qty}@{ask_prc},
            ts={timestamp}
        )""".format(
            venue=self.venue,
            symbol=self.symbol,
            bid_qty=self.bid_qty,
            bid_prc=self.bid_prc,
            ask_qty=self.ask_qty,
            ask_prc=self.ask_prc,
            timestamp=self.timestamp,
        )


class Trade:
    def __init__(self, venue: Venue, symbol: str, timestamp: datetime):
        self.venue = venue
        self.symbol = symbol
        self.price: Optional[float] = None
        self.volume: Optional[float] = None
        self.id: Optional[int] = None
        self.timestamp = timestamp

    def __repr__(self):
        return """Trade (
            venue={venue},
            symbol={symbol},
            price={price},
            volume={volume},
            ts={timestamp}
        )""".format(
            venue=self.venue,
            symbol=self.symbol,
            price=self.price,
            volume=self.volume,
            timestamp=self.timestamp,
        )


class Bar:
    def __init__(
        self,
        venue: Venue,
        symbol: str,
        open: float,
        high: float,
        low: float,
        close: float,
        volume: float,
        timestamp: datetime,
    ):
        self.venue = venue
        self.symbol = symbol
        self.open: float = open
        self.high: float = high
        self.low: float = low
        self.close: float = close
        self.volume: float = volume
        self.trade_count: Optional[float] = None
        self.vwap: Optional[float] = None
        self.exchange: Optional[float] = None
        self.timestamp = timestamp

    def __repr__(self):
        return """Bar (
            venue={venue},
            symbol={symbol},
            open={open},
            high={high},
            low={low},
            close={close},
            volume={volume},
            ts={timestamp}
        )""".format(
            venue=self.venue,
            symbol=self.symbol,
            open=self.open,
            high=self.high,
            low=self.low,
            close=self.close,
            volume=self.volume,
            timestamp=self.timestamp,
        )


class Signal:
    def __init__(
        self, venue: Venue, symbol: str, exposure: Exposure, qty: float, prc: float
    ):
        self.venue = venue
        self.symbol = symbol
        self.exposure = exposure
        self.qty = qty
        self.prc = prc

    def __repr__(self):
        return """Signal (
            venue={venue},
            symbol={symbol},
            exposure={exposure},
            qty={qty},
            prc={prc}
        )""".format(
            venue=self.venue,
            symbol=self.symbol,
            exposure=self.exposure,
            qty=self.qty,
            prc=self.prc,
        )
