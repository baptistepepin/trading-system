import logging
import queue
import sqlite3
from typing import List, Callable

from alpaca_trade_api.common import URL

from data.indicators import add_RSI_indic
from engine.interface import Trade, Quote, Signal, Exposure, Bar
from strategies.strategy import Strategy
from threading import Event
import pandas as pd
import numpy as np
from collections import deque
import alpaca_trade_api as tradeapi


class RSIStrategy(Strategy):
    def __init__(self,
                 config,
                 signal_callback: Callable[[List[Signal]], None],
                 log: logging.Logger,
                 stopEvent: Event):
        super().__init__(config, signal_callback, log, stopEvent)
        self.data_rsi = deque(maxlen=20160)  # 60min * 24h * 14d = 20160
        self.rsi = 0.5
        self.buy = True
        self.sell = True
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
        self.data_rsi.extend(df['close'].tail(20160))  # 60min * 24h * 5d = 20160

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

        self.data_rsi.append(bar.close)

        if len(self.data_rsi) == self.data_rsi.maxlen:
            # Calculate RSI
            df = pd.DataFrame(list(self.data_rsi), columns=['close'])
            rsi = add_RSI_indic(df, column_name='close', window_length=20160)  # 60min * 24h * 14d = 20160

            # Current RSI value
            current_rsi = rsi.iloc[-1].values[0]

            # Determine the trading signal
            if current_rsi <= 30 and self.buy:  # RSI below 30%, potential buy signal
                quantity = self.calculate_position_size(bar.close, 'buy')
                signal = Signal(bar.venue, bar.symbol, Exposure.LONG, quantity, bar.close)
                self.log.debug(f"{self.config['name']} emitting Buy signal: {signal}")
                self._emit_signals([signal])
                self.buy = False
            elif current_rsi > 30 and not self.buy:  # RSI above 30%, reset buy signal
                self.buy = True

            if current_rsi >= 70 and self.sell:  # RSI above 70%, potential sell signal
                quantity = self.calculate_position_size(bar.close, 'sell')
                signal = Signal(bar.venue, bar.symbol, Exposure.SHORT, quantity, bar.close)
                self.log.debug(f"{self.config['name']} emitting Sell signal: {signal}")
                self._emit_signals([signal])
                self.sell = False
            elif current_rsi < 70 and not self.sell:  # RSI below 70%, reset sell signal
                self.sell = True
