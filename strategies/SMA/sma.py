import logging
import queue
import sqlite3
from typing import List, Callable

from alpaca_trade_api.common import URL

from engine.interface import Trade, Quote, Signal, Exposure, Bar
from strategies.strategy import Strategy
from threading import Event
import pandas as pd
import numpy as np
from collections import deque
import alpaca_trade_api as tradeapi


class SMAStrategy(Strategy):
    def __init__(self,
                 config,
                 signal_callback: Callable[[List[Signal]], None],
                 log: logging.Logger,
                 stopEvent: Event):
        super().__init__(config, signal_callback, log, stopEvent)
        self.short_ma = deque(maxlen=7200)  # 60min * 24h * 5d = 7200
        self.long_ma = deque(maxlen=28800)  # 60min * 24h * 20d = 28800
        self.last_buy = False
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
        conn = sqlite3.connect('./data/db_crypto.db')
        df = pd.read_sql_query(f"SELECT * FROM bars WHERE symbol == '{self.config['symbols'][0]}'", conn)  # 0 to get the first symbol
        df.sort_values(by=['timestamp'], inplace=True)
        self.short_ma.extend(df['close'].tail(7200))  # 60min * 24h * 5d = 7200
        self.long_ma.extend(df['close'].tail(28800))  # 60min * 24h * 20d = 28800

    def calculate_position_size(self, price, side):
        account = tradeapi.REST(self.config['api_key'], self.config['secret_key'], base_url=URL('https://paper-api.alpaca.markets'), api_version='v2').get_account()
        self.equity = float(account.equity)
        self.cash = float(account.cash)

        if side == 'buy':
            capital = self.cash
        elif side == 'sell':
            capital = self.equity
        risk_per_trade = 0.02  # 2% of capital
        position_size = (capital * risk_per_trade) / price
        return position_size

    def process_bar(self, bar: Bar):
        self.log.debug(f"strategy processing bar: {bar}")

        self.short_ma.append(bar.close)
        self.long_ma.append(bar.close)

        if len(self.short_ma) == self.short_ma.maxlen and len(self.long_ma) == self.long_ma.maxlen:
            short_sma = np.mean(self.short_ma)
            long_sma = np.mean(self.long_ma)

            # Determine the trading signal
            if short_sma > long_sma and not self.last_buy:
                # Short-term SMA crosses above long-term SMA - Buy Signal
                quantity = self.calculate_position_size(bar.close, 'buy')
                signal = Signal(bar.venue, bar.symbol, Exposure.LONG, quantity, bar.close)
                self.log.debug(f"{self.config['name']} emitting Buy signal: {signal}")
                self._emit_signals([signal])
                self.last_buy = True
            elif short_sma < long_sma and self.last_buy:
                # Short-term SMA crosses below long-term SMA - Sell Signal
                quantity = self.calculate_position_size(bar.close, 'sell')
                signal = Signal(bar.venue, bar.symbol, Exposure.SHORT, quantity, bar.close)
                self.log.debug(f"{self.config['name']} emitting Sell signal: {signal}")
                self._emit_signals([signal])
                self.last_buy = False
