import logging
import queue
from typing import List, Callable
from engine.interface import Trade, Quote, Signal
from strategies.strategy import Strategy
from threading import Event


class Strat1Strategy(Strategy):
    def __init__(
        self,
        config,
        signal_callback: Callable[[List[Signal]], None],
        log: logging.Logger,
        stopEvent: Event,
    ):
        super().__init__(config, signal_callback, log, stopEvent)

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
        pass
