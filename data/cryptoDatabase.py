import logging.config
import alpaca_trade_api as tradeapi
from alpaca_trade_api.common import URL
from alpaca_trade_api.rest import TimeFrame, TimeFrameUnit
import sqlite3
from datetime import datetime, timedelta


class CryptoDatabase:
    def __init__(self, config, log: logging.Logger, start_date):
        self.log = log
        self.databaseLog = logging.getLogger('database')
        self.symbols = config['database']['symbols_crypto']
        self.api = tradeapi.REST(config['database']['api_key'],
                                 config['database']['secret_key'],
                                 base_url=URL('https://paper-api.alpaca.markets'),
                                 api_version='v2')
        self.conn = None
        self.cursor = None
        self.open()
        self.initialize_database()
        self.populate_database(start_date)

    def initialize_database(self):
        self.databaseLog.info('Initializing database...')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS bars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                symbol TEXT,
                close REAL,
                high REAL,
                low REAL,
                trade_count INTEGER,
                open REAL,
                volume REAL,
                vwap REAL,
                added_on DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    def populate_database(self, start_date):
        end_date = datetime.now().date()
        current_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        while current_date <= end_date:
            self.add_data_for_date(current_date.strftime('%Y-%m-%d'))
            current_date += timedelta(days=1)
        self.remove_duplicates()

    def add_data_for_date(self, date):
        next_date = (datetime.strptime(date, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
        bars = self.api.get_crypto_bars(self.symbols, TimeFrame(1, TimeFrameUnit.Minute), date, next_date).df
        bars.index = bars.index.tz_convert(None)
        bars.reset_index(inplace=True)
        bars['timestamp'] = bars['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
        self.databaseLog.info(f'Adding data ({len(bars.index)}) from {date} to the database...')
        bars.to_sql('bars', self.conn, if_exists='append', index=False)

    def remove_duplicates(self):
        self.cursor.execute('''
            CREATE TEMPORARY TABLE latest_entries AS
            SELECT MAX(id) AS max_id
            FROM bars
            GROUP BY timestamp, symbol
        ''')

        self.cursor.execute('''
            DELETE FROM bars
            WHERE id NOT IN (SELECT max_id FROM latest_entries)
        ''')

        self.conn.commit()

    def update_database(self):
        self.open()
        last_date = self.cursor.execute('SELECT MAX(timestamp) FROM bars').fetchone()[0][:10]  # We are adding an entire day every time
        # So there is an overlapping TODO: Fix this to look at the timestamp and add the missing data only
        if last_date:
            self.populate_database(last_date)
        self.close()

    def open(self):
        if self.conn is None:
            self.conn = sqlite3.connect('db_crypto.db')
            self.cursor = self.conn.cursor()

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None
