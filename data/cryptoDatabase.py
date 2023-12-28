import logging.config
import sqlite3
from datetime import datetime, timedelta
from alpaca.data.historical.crypto import CryptoHistoricalDataClient
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.data.requests import CryptoBarsRequest


class CryptoDatabase:
    def __init__(self, config, log: logging.Logger):
        self.log = log
        self.databaseLog = logging.getLogger("database")
        self.symbols = config["database"]["crypto"]["symbols"]
        self.start_date = config["database"]["start_date"]
        self.api = CryptoHistoricalDataClient(
            api_key=config["database"]["api_key"],
            secret_key=config["database"]["secret_key"],
        )
        self.conn = None
        self.cursor = None
        self.open()
        self.initialize_database()
        self.populate_database()
        self.close()

    def initialize_database(self):
        self.databaseLog.info("Initializing database...")
        self.cursor.execute(
            """
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
        """
        )
        self.conn.commit()

    def populate_database(self):
        end_date = datetime.now()
        current_date = datetime.strptime(self.start_date, "%Y-%m-%d")
        while current_date <= end_date:
            self.add_data_for_date(current_date)
            current_date += timedelta(days=1)
        self.remove_duplicates()

    def add_data_for_date(self, date: datetime):
        end_date = date + timedelta(days=1)
        bars = self.api.get_crypto_bars(
            request_params=CryptoBarsRequest(
                symbol_or_symbols=self.symbols,
                timeframe=TimeFrame(1, TimeFrameUnit.Minute),
                start=date,
                end=end_date,
            )
        ).df
        self.databaseLog.info(
            f"Adding data ({len(bars.index)}) from {date} to the database..."
        )
        bars.to_sql("bars", self.conn, if_exists="append", index=True)

    def remove_duplicates(self):
        self.cursor.execute(
            """
            CREATE TEMPORARY TABLE latest_entries AS
            SELECT MAX(id) AS max_id
            FROM bars
            GROUP BY timestamp, symbol
        """
        )

        self.cursor.execute(
            """
            DELETE FROM bars
            WHERE id NOT IN (SELECT max_id FROM latest_entries)
        """
        )

        self.conn.commit()

    def update_database(self):
        self.open()
        q = """
        SELECT MAX(timestamp) FROM {table}
        """.format(
            table="bars",
        )
        # We are adding an entire day every time
        last_date = self.cursor.execute(q).fetchone()[0][:10]
        # So there is an overlapping
        # TODO: Fix this to look at the timestamp
        # and add the missing data only
        if last_date:
            self.populate_database(last_date)
        self.close()

    def open(self):
        if self.conn is None:
            self.conn = sqlite3.connect("./data/db_crypto.db")
            self.cursor = self.conn.cursor()

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None
