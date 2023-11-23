# standard
import logging
from abc import ABC, abstractmethod
from threading import Thread
from typing import List, Callable
from engine.interface import Quote, Trade


class Gateway(ABC, Thread):
    """
    Abstract gateway interface
    """

    def __init__(self,
                 config: dict,
                 quote_callback: Callable[[List[Quote]], None],
                 trade_callback: Callable[[List[Trade]], None],
                 log: logging.Logger):
        super().__init__(name=f"{config['name']}")
        self.config = config
        self.quote_cb = quote_callback
        self.trade_cb = trade_callback
        self.log = log

    @abstractmethod
    def activate(self):
        raise NotImplementedError

    @abstractmethod
    def deactivate(self):
        raise NotImplementedError

    @abstractmethod
    def subscribe(self, symbols: List[str] = None):
        raise NotImplementedError

    @abstractmethod
    def unsubscribe(self, symbols: List[str] = None):
        raise NotImplementedError

    def run(self):
        self.log.info(f"{self.name} starting")
        self.subscribe()
        self.activate()

    def stop(self):
        self.log.info(f"{self.name} stopping")
        self.deactivate()
