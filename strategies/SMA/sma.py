import logging
import queue
from typing import List, Callable
from engine.interface import Trade, Quote, Signal, Exposure
from strategies.strategy import Strategy
from threading import Event
import pandas as pd
import numpy as np
from collections import deque


class SMAStrategy(Strategy):
    def __init__(self,
                 config,
                 signal_callback: Callable[[List[Signal]], None],
                 log: logging.Logger,
                 stopEvent: Event):
        super().__init__(config, signal_callback, log, stopEvent)
        self.short_bid = deque(maxlen=10)
        self.long_bid = deque(maxlen=20)
        self.short_ask = deque(maxlen=10)
        self.long_ask = deque(maxlen=20)
        self.df_book = pd.DataFrame(columns=['timestamp', 'bid_price', 'bid_qty', 'ask_price', 'ask_qty', 'signal'])

    def handle_trades(self, trades: List[Trade]):
        pass  # do not consume trades

    def run(self):
        self.log.info(f"{self.config['name']} started")
        while not self.stopEvent.is_set():
            try:
                quote = self.quoteBuffer.get(timeout=1)
            except queue.Empty:
                pass
            else:
                self.process_quote(quote)
        self.log.info(f"{self.config['name']} stopped")

    def process_quote(self, quote: Quote):
        self.log.debug(f"strategy processing quote: {quote}")
        self.short_bid.append(quote.bid_prc)
        self.long_bid.append(quote.bid_prc)
        self.short_ask.append(quote.ask_prc)
        self.long_ask.append(quote.ask_prc)
        short_bid_prc = sum(self.short_bid) / len(self.short_bid)
        long_bid_prc = sum(self.long_bid) / len(self.long_bid)
        short_ask_prc = sum(self.short_ask) / len(self.short_ask)
        long_ask_prc = sum(self.long_ask) / len(self.long_ask)

        if short_ask_prc > long_ask_prc:
            signal = Signal(quote.venue, quote.symbol, Exposure.LONG, quote.ask_qty, quote.ask_prc)
            self.log.debug(f"{self.config['name']} emitting {signal}")
            self._emit_signals([signal])
        elif short_bid_prc > long_bid_prc:
            signal = Signal(quote.venue, quote.symbol, Exposure.SHORT, quote.bid_qty, quote.bid_prc)
            self.log.debug(f"{self.config['name']} emitting {signal}")
            self._emit_signals([signal])
