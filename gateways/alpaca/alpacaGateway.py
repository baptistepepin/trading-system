# standard
import logging
import alpaca
from typing import List, Callable
from alpaca.data.live.crypto import CryptoDataStream
# local
from engine.interface import Trade, Quote, Venue
from gateways import gateway


class AlpacaGateway(gateway.Gateway):
    def __init__(self,
                 config: dict,
                 quote_callback: Callable[[List[Quote]], None],
                 trade_callback: Callable[[List[Trade]], None],
                 log: logging.Logger):
        super().__init__(config, quote_callback, trade_callback, log)
        self.stream = CryptoDataStream(
            self.config['api_key'],
            self.config['secret_key'],
            raw_data=False,
            url_override=self.config['endpoints']['market_data']['crypto']
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

    def subscribe(self, symbols=None):
        symbols = symbols if symbols else self.config['symbols']
        if symbols:
            self.stream.subscribe_quotes(self._on_quote, *symbols)
            self.stream.subscribe_trades(self._on_trade, *symbols)

    def unsubscribe(self, symbols=None):
        symbols = symbols if symbols else self.config['symbols']
        if symbols:
            self.stream.unsubscribe_quotes(*symbols)
            self.stream.unsubscribe_trades(*symbols)

    def activate(self):
        self.stream.run()

    def deactivate(self):
        self.stream.stop()

