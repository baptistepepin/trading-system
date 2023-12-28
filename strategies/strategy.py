# standard
import logging
from typing import List, Callable
from abc import ABC, abstractmethod
from queue import SimpleQueue
from threading import Thread, Event

# local
from engine.interface import Trade, Quote, Signal, Bar


class Strategy(ABC, Thread):
    def __init__(
        self,
        config: dict,
        signal_callback: Callable[[List[Signal]], None],
        log: logging.Logger,
        stopEvent: Event,
    ):
        super().__init__(name=f"{config['name']}")
        self.config = config
        self.log = log
        self.signal_cb = signal_callback
        self.quoteBuffer = SimpleQueue()
        self.tradeBuffer = SimpleQueue()
        self.barBuffer = SimpleQueue()
        self.stopEvent = stopEvent

    def handle_quotes(self, quotes: List[Quote]):
        for quote in quotes:
            self.quoteBuffer.put(quote)

    def handle_trades(self, trades: List[Trade]):
        for trade in trades:
            self.tradeBuffer.put(trade)

    def handle_bars(self, bars: List[Bar]):
        for bar in bars:
            self.barBuffer.put(bar)

    def _emit_signals(self, signals: List[Signal]):
        self.signal_cb(signals)

    @abstractmethod
    def run(self):
        raise NotImplementedError
