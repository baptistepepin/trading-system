# standard
import logging
import queue
import pyodbc
from multiprocessing.context import Process
from queue import SimpleQueue
from collections import defaultdict
from multiprocessing import Pipe
from threading import Event, Thread
from typing import Dict, Callable, DefaultDict, List

from alpaca.trading import MarketOrderRequest, TimeInForce, OrderType

# local
from engine.interface import Trade, Quote, Signal, Venue, StrategyType, StrategyTypeMap, VenueMap, ExposureToSideMap
from gateways.alpaca.alpacaGateway import AlpacaGateway
from gui.dashboard import spawn_dashboard
from strategies.SMA.sma import SMAStrategy
from strategies.strategy import Strategy
from gateways.gateway import Gateway


gatewayFactory: Dict[int, Callable[..., Gateway]] = {
    Venue.ALPACA: lambda cfg, qcb, tcb, log: AlpacaGateway(cfg, qcb, tcb, log)
}

strategyFactory: Dict[int, Callable[..., Strategy]] = {
    StrategyType.SMA: lambda cfg, qcb, log, stopper: SMAStrategy(cfg, qcb, log, stopper)
}


class Engine(Thread):
    def __init__(self, config, log: logging.Logger):
        super().__init__(name="engine")
        self.log: logging.Logger = log
        self.dataLog = logging.getLogger('data')
        self.routing: DefaultDict[int, DefaultDict[str, List[Strategy]]] = defaultdict(lambda: defaultdict(list))
        self.gateways: List[Gateway] = []
        self.strategies: List[Strategy] = []
        self.signalBuffer = SimpleQueue()
        self.stopEvent = Event()
        # rx, self.tx = Pipe(duplex=False)
        # self.dashproc = Process(target=spawn_dashboard, args=(rx,))
        #
        # try:
        #     self.dbcxn: pyodbc.Connection = pyodbc.connect(dsn=config['odbc']['dsn'], autocommit=True)
        #     self.dbcxn.setdecoding(pyodbc.SQL_WCHAR, encoding='utf-8')
        #     self.dbcxn.setencoding(encoding='utf-8')
        #     # self.dbcxn.maxwrite = TODO documentation claims this needs to be arbitrarily large to avoid slow writes
        # except Exception as e:
        #     log.critical(f'database failure: {e}')
        #     exit(1)

        # setup gateways
        for venueCfg in config['venues']:
            try:
                v = VenueMap[venueCfg['api']]
                gateway = gatewayFactory[v](venueCfg, self.handle_quotes, self.handle_trades, log)
                self.gateways.append(gateway)
            except KeyError:
                log.critical(f"unsupported venue: {venueCfg['api']}")
                exit(1)
            except Exception as e:
                log.critical(f"failed to instantiate gateway: {venueCfg['api']}")
                exit(1)

        # setup strategies
        for strategyCfg in config['strategies']:
            try:
                st = StrategyTypeMap[strategyCfg['type']]
                strategy = strategyFactory[st](strategyCfg, self.handle_signals, log, self.stopEvent)
                for venue in strategyCfg['venues']:
                    v = VenueMap[venue]
                    for symbol in strategyCfg['symbols']:
                        self.routing[v][symbol].append(strategy)
                self.strategies.append(strategy)
            except KeyError:
                log.critical(f"unsupported venue: {strategyCfg['api']}")
                exit(1)
            except Exception as e:
                log.critical(f"failed to instantiate strategy: {strategyCfg['api']}")
                exit(1)

    def run(self):
        self.log.info("engine started")
        # self.dashproc.start()
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
        # self.dashproc.terminate()
        # self.dashproc.join()
        self.log.info("engine stopped")

    def handle_quotes(self, quotes: List[Quote]):
        for quote in quotes:
            self.dataLog.info(quote)
            # self.tx.send(quote)
            for strategy in self.routing[quote.venue][quote.symbol]:
                strategy.handle_quotes([quote])

    def handle_trades(self, trades: List[Trade]):
        for trade in trades:
            self.dataLog.info(trade)
            # self.tx.send(trade)
            for strategy in self.routing[trade.venue][trade.symbol]:
                strategy.handle_trades([trade])

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

    def sig_handler(self, signum, frame):  # TODO this is a hack, need to fix this
        self.log.info(f"Received signal: {signum}. Initiating shutdown.")
        self.stopEvent.set()
