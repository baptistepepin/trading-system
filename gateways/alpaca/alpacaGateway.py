# standard
import logging
import alpaca
from typing import List, Callable
from alpaca.data.live import StockDataStream
from alpaca.data.live.crypto import CryptoDataStream
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest

from engine.interface import Trade, Quote, Venue, Bar
from gateways import gateway


class AlpacaGateway(gateway.Gateway):
    def __init__(
        self,
        config: dict,
        quote_callback: Callable[[List[Quote]], None],
        trade_callback: Callable[[List[Trade]], None],
        bar_callback: Callable[[List[Bar]], None],
        log: logging.Logger,
    ):
        super().__init__(config, quote_callback, trade_callback, bar_callback, log)
        self.streamCrypto = CryptoDataStream(
            api_key=self.config["api_key"],
            secret_key=self.config["secret_key"],
            raw_data=False,
        )
        self.streamStocks = StockDataStream(
            api_key=self.config["api_key"],
            secret_key=self.config["secret_key"],
            raw_data=False,
        )
        self.trading = TradingClient(
            api_key=self.config["api_key"],
            secret_key=self.config["secret_key"],
            paper=self.config["paper"],
        )

    async def _on_quote(self, update: alpaca.data.models.quotes.Quote):
        quote = Quote(Venue.ALPACA, update.symbol, update.timestamp)
        quote.bid_prc = update.bid_price
        quote.ask_prc = update.ask_price
        quote.bid_qty = update.bid_size
        quote.ask_qty = update.ask_size
        self.quote_cb([quote])

    async def _on_trade(self, update: alpaca.data.models.trades.Trade):
        trade = Trade(Venue.ALPACA, update.symbol, update.timestamp)
        trade.price = update.price
        trade.volume = update.size
        trade.id = update.id
        self.trade_cb([trade])

    async def _on_bars(self, update: alpaca.data.models.bars.Bar):
        bar = Bar(
            Venue.ALPACA,
            update.symbol,
            update.open,
            update.high,
            update.low,
            update.close,
            update.volume,
            update.timestamp,
        )
        self.bar_cb([bar])

    def subscribe(self, symbols_crypto=None, symbols_stocks=None):
        symbols_crypto = (
            symbols_crypto if symbols_crypto else self.config["symbols_crypto"]
        )
        if symbols_crypto:
            self.streamCrypto.subscribe_quotes(self._on_quote, *symbols_crypto)
            self.streamCrypto.subscribe_trades(self._on_trade, *symbols_crypto)
            self.streamCrypto.subscribe_bars(self._on_bars, *symbols_crypto)

        # if symbols_stocks is None:
        #     symbols_stocks = self.config['symbols_stocks']
        # self.streamStocks.subscribe_quotes(*symbols_stocks)
        # self.streamStocks.subscribe_trades(*symbols_stocks)
        # self.streamStocks.subscribe_bars(*symbols_stocks)

    def unsubscribe(self, symbols_crypto=None, symbols_stocks=None):
        symbols_crypto = (
            symbols_crypto if symbols_crypto else self.config["symbols_crypto"]
        )
        if symbols_crypto:
            self.streamCrypto.unsubscribe_quotes(*symbols_crypto)
            self.streamCrypto.unsubscribe_trades(*symbols_crypto)
            self.streamCrypto.unsubscribe_bars(*symbols_crypto)

        # if symbols_stocks is None:
        #     symbols_stocks = self.config['symbols_stocks']
        # self.streamStocks.unsubscribe_quotes(*symbols_stocks)
        # self.streamStocks.unsubscribe_trades(*symbols_stocks)
        # self.streamStocks.unsubscribe_bars(*symbols_stocks)

    def activate(self):
        self.streamCrypto.run()
        # self.streamStocks.run()

    def deactivate(self):
        self.streamCrypto.stop()
        # self.streamStocks.stop()

    def trade(self, market_order: MarketOrderRequest):
        try:
            self.trading.submit_order(order_data=market_order)
        except Exception as e:
            self.log.error(f"failed to submit order: {e}")
