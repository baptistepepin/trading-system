import alpaca_trade_api as tradeapi
from alpaca_trade_api.common import URL
from alpaca_trade_api.rest import REST, TimeFrame, TimeFrameUnit
import sqlite3


API_KEY = 'PKPN404QD7XJI5WRH41C'
API_SECRET = 'BN9cnjvRFnXOSXlbkAv6LxLDUp41LbrwZSgOsmXD'
BASE_URL = URL('https://paper-api.alpaca.markets')
api = tradeapi.REST(API_KEY, API_SECRET, base_url=BASE_URL, api_version='v2')


conn = sqlite3.connect('db_crypto.db')

cursor = conn.cursor()

assets = ['BTC/USD', 'ETH/USD']

cursor.execute('''
    CREATE TABLE IF NOT EXISTS crypto_bars (
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

conn.commit()

bars = api.get_crypto_bars(assets, TimeFrame(1, TimeFrameUnit.Day), "2019-01-01", "2023-11-23").df
bars.index = bars.index.tz_convert(None)
bars.reset_index(inplace=True)
bars['timestamp'] = bars['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
bars.to_sql('crypto_bars', conn, if_exists='append', index=False)

cursor.execute('''
    CREATE TEMPORARY TABLE latest_entries AS
    SELECT MAX(id) AS max_id
    FROM crypto_bars
    GROUP BY timestamp, symbol
''')

cursor.execute('''
    DELETE FROM crypto_bars
    WHERE id NOT IN (SELECT max_id FROM latest_entries)
''')

conn.commit()
conn.close()
