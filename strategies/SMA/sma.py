import logging
import queue
import sqlite3
from typing import List, Callable
from engine.interface import Trade, Quote, Signal, Exposure, Bar
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
        self.short_bid = deque(maxlen=28800)
        self.long_bid = deque(maxlen=72000)
        self.init_deque()

    def run(self):
        self.log.info(f"{self.config['name']} started")
        while not self.stopEvent.is_set():
            try:
                bar = self.barBuffer.get(timeout=1)
            except queue.Empty:
                pass
            else:
                self.process_bar(bar)
        self.log.info(f"{self.config['name']} stopped")

    def init_deque(self):
        conn = sqlite3.connect('db_crypto.db')
        df = pd.read_sql_query(f"SELECT * FROM bars WHERE symbol == '{self.config['symbols'][0]}'", conn)  # 0 to get the first symbol
        df.sort_values(by=['timestamp'], inplace=True)
        self.short_bid.extend(df['close'].tail(28800))  # 60min * 24h * 20d = 28800
        self.long_bid.extend(df['close'].tail(72000))  # 60min * 24h * 50d = 72000

    def process_bar(self, bar: Bar):
        self.log.debug(f"strategy processing bar: {bar}")

        self.short_bid.append(bar.close)
        self.long_bid.append(bar.close)

        if len(self.short_bid) == self.short_bid.maxlen and len(self.long_bid) == self.long_bid.maxlen:
            short_sma = np.mean(self.short_bid)
            long_sma = np.mean(self.long_bid)

            # Determine the trading signal
            # TODO: Add a better way to choose quantity to sell and buy
            if short_sma > long_sma:
                # Short-term SMA crosses above long-term SMA - Buy Signal
                signal = Signal(bar.venue, bar.symbol, Exposure.LONG, 0.01, bar.close)
                self.log.debug(f"{self.config['name']} emitting Buy signal: {signal}")
                self._emit_signals([signal])
            elif short_sma < long_sma:
                # Short-term SMA crosses below long-term SMA - Sell Signal
                signal = Signal(bar.venue, bar.symbol, Exposure.SHORT, 0.01, bar.close)
                self.log.debug(f"{self.config['name']} emitting Sell signal: {signal}")
                self._emit_signals([signal])
