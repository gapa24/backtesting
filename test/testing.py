# from src.data_loader import load_data

# # test 1 — CSV full history 15min
# df = load_data("15min", "full")
# print('Test 1 — CSV full history 15min')
# print(df.shape)        # should be (rows, 5)
# print(df.head())
# print(df.dtypes)

# print('Test 2 — yfinance last 60 days 15min')
# df = load_data("15min", "60d")
# print(df.shape)
# print(df.tail())

# # test 3 — custom interval (resamples from 1min CSV)
# df = load_data("10min", "full")
# print('Test 3 — custom interval (resamples from 1min CSV)')
# print(df.shape)
# print(df.index[0])     # should be 09:15:00





print("Testing backtesting framework...")
from app.data_loader import load_data
from app.backtest_runner import run_backtest

df = load_data("15min", "full")

code = """
import pandas_ta as ta

def generate_signals(df):
    df['sma44'] = ta.sma(df['Close'], length=44)
    df['atr']   = ta.atr(df['High'], df['Low'], df['Close'], length=14)

    bull = (
        (df['Close'] > df['Open']) &
        (df['Open']  <= df['Close'].shift(1)) &
        (df['Close'] >= df['Open'].shift(1))
    )
    bear = (
        (df['Close'] < df['Open']) &
        (df['Open']  >= df['Close'].shift(1)) &
        (df['Close'] <= df['Open'].shift(1))
    )

    near_ma = df['sma44'].notna() & (
        abs(df['Close'] - df['sma44']) <= df['atr'] * 0.2
    )

    long_cond  = (df['Close'] > df['sma44']) & near_ma & bull
    short_cond = (df['Close'] < df['sma44']) & near_ma & bear

    df['signal']      = 0
    df['stop_loss']   = None
    df['take_profit'] = None

    df.loc[long_cond,  'signal']      = 1
    df.loc[long_cond,  'stop_loss']   = df['Low']
    df.loc[long_cond,  'take_profit'] = df['Close'] + (df['Close'] - df['Low']) * 1.5

    df.loc[short_cond, 'signal']      = -1
    df.loc[short_cond, 'stop_loss']   = df['High']
    df.loc[short_cond, 'take_profit'] = df['Close'] - (df['High'] - df['Close']) * 1.5

    return df
"""

print(df.head())
result = run_backtest(code, df)

print("Metrics:", result["metrics"])
print("Total signals:", len(result["signals"]))
print("Total candles:", len(result["candles"]))
print("Equity curve points:", len(result["equity_curve"]))
print("Recent trades:", result["trades"][:3])