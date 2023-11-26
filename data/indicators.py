import pandas as pd

# Calculate some technical indicators


def add_mov_average(data, column_name, window):
    if column_name not in data.columns:
        return
    data[column_name + " Moving Average " + str(window)] = data[column_name].rolling(window).mean()


def add_mov_std(data, column_name, window):
    if column_name not in data.columns:
        return
    data[column_name + " Moving Std " + str(window)] = data[column_name].rolling(window).std()


def add_mov_dynamic(data, column_name, window):
    if column_name not in data.columns:
        return
    dynamic_col = (data[column_name] - data[column_name].rolling(window).mean()) / data[column_name].rolling(
        window).std()
    data[column_name + " Dynamic " + str(window)] = dynamic_col


def add_macd_indic(data, column_name):
    if column_name not in data.columns:
        return
    e26 = pd.Series.ewm(data[column_name], span=26).mean()
    e12 = pd.Series.ewm(data[column_name], span=12).mean()
    MACD = e12 - e26
    diff_MACD_e9 = MACD - pd.Series.ewm(MACD, span=9).mean()
    data[column_name + " MACD"] = diff_MACD_e9


def add_RSI_indic(data, column_name='close', window_length=14):
    if column_name not in data.columns:
        return
    returns = data[column_name] - data[column_name].shift()
    gains = returns * (returns >= 0).astype(int)
    losses = returns * (returns <= 0).astype(int)
    avg_gains = [0] * window_length + [gains[1:window_length + 1].mean()]
    avg_losses = [0] * window_length + [losses[1:window_length + 1].mean()]
    for i in range(len(avg_gains), len(gains)):
        avg_gains.append((avg_gains[i - 1] * 13 + gains[i]) / 14)
        avg_losses.append((avg_losses[i - 1] * 13 + losses[i]) / 14)
    RSI = 100 - (100 / (1 + pd.DataFrame(avg_gains) / -pd.DataFrame(avg_losses)))
    RSI.index = data.index
    data[column_name + " RSI"] = RSI


def add_ATR_indic(data, column_name='close', window_length=14):
    a = data["high"] - data["low"]
    b = abs(data["high"] - data[column_name])
    c = abs(data["low"] - data[column_name])
    TR = pd.DataFrame({'a': a, 'b': b, 'c': c}).max(axis=1)
    data["ATR " + column_name] = TR.rolling(window_length).mean()


def create_indicators(data):
    symbols = data['symbol'].unique()

    res = []

    for symbol in symbols:
        df = data[data['symbol'] == symbol]
        add_mov_average(df, 'close', 20)
        add_mov_average(df, 'close', 50)
        add_mov_average(df, 'close', 200)
        add_mov_std(df, 'close', 20)
        add_mov_std(df, 'close', 50)
        add_mov_std(df, 'close', 200)
        add_mov_dynamic(df, 'close', 20)
        add_mov_dynamic(df, 'close', 50)
        add_mov_dynamic(df, 'close', 200)
        add_macd_indic(df, 'close')
        # add_RSI_indic(df)
        add_ATR_indic(df)

        res.append(df)

    return pd.concat(res)
