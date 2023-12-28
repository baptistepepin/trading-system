# standard
import logging
import queue

import pandas as pd
from multiprocessing.context import Process
from queue import SimpleQueue
from collections import defaultdict
from multiprocessing import Pipe
from threading import Event, Thread
from typing import Dict, Callable, DefaultDict, List

from alpaca.trading import MarketOrderRequest, TimeInForce, OrderType

# local
from engine.interface import (
    Trade,
    Quote,
    Signal,
    Venue,
    StrategyType,
    StrategyTypeMap,
    VenueMap,
    ExposureToSideMap,
    Bar,
)
from gateways.alpaca.alpacaGateway import AlpacaGateway
from gui.dashboard import spawn_dashboard
from strategies.RSI.rsi import RSIStrategy
from strategies.SMA.sma import SMAStrategy
from strategies.Strat1.Strat1 import Strat1Strategy
from strategies.strategy import Strategy
from gateways.gateway import Gateway


gatewayFactory: Dict[int, Callable[..., Gateway]] = {
    Venue.ALPACA: lambda cfg, qcb, tcb, bcb, log: AlpacaGateway(cfg, qcb, tcb, bcb, log)
}

strategyFactory: Dict[int, Callable[..., Strategy]] = {
    StrategyType.SMA: lambda cfg, scb, log, stopper: SMAStrategy(
        cfg, scb, log, stopper
    ),
    StrategyType.RSI: lambda cfg, scb, log, stopper: RSIStrategy(
        cfg, scb, log, stopper
    ),
    StrategyType.Strat1: lambda cfg, scb, log, stopper: Strat1Strategy(
        cfg, scb, log, stopper
    ),
}


class Engine(Thread):
    def __init__(self, config, log: logging.Logger, cryptoDatabase):
        super().__init__(name="engine")
        self.log: logging.Logger = log
        self.dataLog = logging.getLogger("data")
        self.routing: DefaultDict[int, DefaultDict[str, List[Strategy]]] = defaultdict(
            lambda: defaultdict(list)
        )
        self.gateways: List[Gateway] = []
        self.strategies: List[Strategy] = []
        self.signalBuffer = SimpleQueue()
        self.stopEvent = Event()
        self.dbcxn = cryptoDatabase
        rx, self.tx = Pipe(duplex=False)
        self.dashproc = Process(target=spawn_dashboard, args=(rx,))

        try:
            self.dbcxn.open()
            self.dbcxn.close()
        except Exception as e:
            log.critical(f"database failure: {e}")
            exit(1)

        # setup gateways
        for venueCfg in config["venues"]:
            try:
                v = VenueMap[venueCfg["api"]]
                gateway = gatewayFactory[v](
                    venueCfg,
                    self.handle_quotes,
                    self.handle_trades,
                    self.handle_bars,
                    log,
                )
                self.gateways.append(gateway)
            except KeyError:
                log.critical(f"unsupported venue: {venueCfg['api']}")
                exit(1)
            except Exception:
                log.critical(f"failed to instantiate gateway: {venueCfg['api']}")
                exit(1)

        # setup strategies
        for strategyCfg in config["strategies"]:
            try:
                st = StrategyTypeMap[strategyCfg["type"]]
                strategy = strategyFactory[st](
                    strategyCfg, self.handle_signals, log, self.stopEvent
                )
                for venue in strategyCfg["venues"]:
                    v = VenueMap[venue]
                    for symbol in strategyCfg["symbols"]:
                        self.routing[v][symbol].append(strategy)
                self.strategies.append(strategy)
            except KeyError as e:
                log.critical(f"unsupported venue: {e}")
                exit(1)
            except Exception as e:
                log.critical(f"failed to instantiate strategy: {e}")
                exit(1)

    def run(self):
        self.log.info("engine started")
        self.dashproc.start()
        threads: List[Thread] = []
        threads.extend(self.strategies)
        threads.extend(self.gateways)
        list(t.start() for t in threads)
        while not self.stopEvent.is_set():
            try:
                sig = self.signalBuffer.get(timeout=1)
            except queue.Empty:
                pass
            else:
                self.log.debug(f"engine processing signal: {sig}")
        self.log.info("engine stopping")
        list(g.stop() for g in self.gateways)
        list(t.join() for t in threads)
        self.dashproc.terminate()
        self.dashproc.join()
        self.log.info("engine stopped")

    def handle_quotes(self, quotes: List[Quote]):
        for quote in quotes:
            self.dataLog.info(quote)
            # TODO: add a quote message in database log
            self.dbcxn.open()
            quote_df = pd.DataFrame(
                [
                    [
                        quote.timestamp,
                        quote.symbol,
                        quote.bid_prc,
                        quote.bid_qty,
                        quote.ask_prc,
                        quote.ask_qty,
                    ]
                ],
                columns=[
                    "timestamp",
                    "symbol",
                    "bid_price",
                    "bid_qty",
                    "ask_price",
                    "ask_qty",
                ],
            )
            quote_df.to_sql("quotes", self.dbcxn.conn, if_exists="append", index=False)
            self.dbcxn.conn.commit()
            self.dbcxn.close()
            # self.tx.send(quote)
            for strategy in self.routing[quote.venue][quote.symbol]:
                strategy.handle_quotes([quote])

    def handle_trades(self, trades: List[Trade]):
        for trade in trades:
            self.dataLog.info(trade)
            # self.tx.send(trade)
            for strategy in self.routing[trade.venue][trade.symbol]:
                strategy.handle_trades([trade])

    def handle_bars(self, bars: List[Bar]):
        for bar in bars:
            self.dataLog.info(bar)
            self.dbcxn.update_database()
            self.tx.send(bar)
            for strategy in self.routing[bar.venue][bar.symbol]:
                strategy.handle_bars([bar])

    def handle_signals(self, signals: List[Signal]):
        for signal in signals:
            self.dataLog.info(signal)
            # self.tx.send(signal)

            market_order_data = MarketOrderRequest(
                order_type=OrderType.MARKET,
                symbol=signal.symbol,
                qty=signal.qty,
                side=ExposureToSideMap[signal.exposure],
                time_in_force=TimeInForce.GTC,
            )

            self.gateways[0].trade(market_order_data)  # 0 is hardcoded for Alpaca

    def sig_handler(self, signum, frame):
        self.log.info(f"Received signal: {signum}. Initiating shutdown.")
        self.stopEvent.set()
