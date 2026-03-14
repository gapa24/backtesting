import pandas as pd
import pandas_ta as ta
import numpy as np
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
import traceback
import types


BLOCKED_KEYWORDS = [
    "import os", "import sys", "import subprocess",
    "open(", "exec(", "eval(", "__import__",
    "shutil", "socket", "requests", "urllib",
]


def run_backtest(code: str, df: pd.DataFrame, cash: float = 100000) -> dict:
    """
    Main entry point.

    Args:
        code  : user's Python strategy code string (must define generate_signals)
        df    : clean OHLCV DataFrame from data_loader
        cash  : starting capital (default 100,000)

    Returns:
        dict with keys: candles, signals, metrics, equity_curve
    """
    # step 1 — safety check
    _safety_check(code)

    # step 2 — execute user code and extract generate_signals function
    generate_signals = _extract_function(code)

    # step 3 — capitalize columns so backtesting.py is happy (Open/High/Low/Close/Volume)
    #           user's generate_signals must also use capitalized column names
    df = df.copy()
    df.columns = [col.capitalize() for col in df.columns]

    # step 4 — run generate_signals on df to get signal columns
    df = _apply_signals(df, generate_signals)

    # step 5 — build backtesting.py Strategy class dynamically
    bt_strategy = _build_strategy(df)

    # step 6 — run backtest
    bt = Backtest(
        df,
        bt_strategy,
        cash=cash,
        commission=0.0002,  # 0.02% per trade — realistic for NSE
        exclusive_orders=True,
    )
    stats = bt.run()

    # step 7 — package results
    return _package_results(df, stats)


def _safety_check(code: str):
    for keyword in BLOCKED_KEYWORDS:
        if keyword in code:
            raise ValueError(
                f"Blocked keyword detected: '{keyword}'. "
                "For security reasons, system-level operations are not allowed."
            )


def _extract_function(code: str):
    namespace = {"pd": pd, "ta": ta, "np": np}
    try:
        exec(compile(code, "<strategy>", "exec"), namespace)
    except SyntaxError as e:
        raise ValueError(f"Syntax error in your strategy code: {e}")
    except Exception as e:
        raise ValueError(f"Error loading strategy code: {e}")

    if "generate_signals" not in namespace:
        raise ValueError(
            "Function 'generate_signals' not found. "
            "Make sure your code defines: def generate_signals(df):"
        )

    fn = namespace["generate_signals"]
    if not callable(fn):
        raise ValueError("'generate_signals' must be a function.")

    return fn


def _apply_signals(df: pd.DataFrame, generate_signals) -> pd.DataFrame:
    # note: df already has capitalized OHLCV columns here (Open/High/Low/Close/Volume)
    # user's generate_signals must use capitalized names too
    try:
        df = generate_signals(df)
    except Exception as e:
        raise ValueError(
            f"Error inside generate_signals: {e}\n{traceback.format_exc()}"
        )

    required = {"signal", "stop_loss", "take_profit"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"generate_signals must add these columns to df: {required}. "
            f"Missing: {missing}"
        )

    # validate signal values
    valid_signals = {-1, 0, 1}
    unique_signals = set(df["signal"].dropna().unique())
    invalid = unique_signals - valid_signals
    if invalid:
        raise ValueError(
            f"signal column contains invalid values: {invalid}. "
            "Only 1 (buy), -1 (sell), 0 (hold) are allowed."
        )

    return df


def _build_strategy(df: pd.DataFrame):
    """
    Dynamically builds a backtesting.py Strategy class
    using the signal, stop_loss, take_profit columns from df.
    """

    class DynamicStrategy(Strategy):

        def init(self):
            # expose signal columns as indicators
            self.signal      = self.I(lambda: df["signal"].values,      name="signal")
            self.stop_loss   = self.I(lambda: df["stop_loss"].values,   name="stop_loss")
            self.take_profit = self.I(lambda: df["take_profit"].values, name="take_profit")

        def next(self):
            sig = self.signal[-1]
            sl  = self.stop_loss[-1]
            tp  = self.take_profit[-1]

            # skip if no signal or SL/TP not defined
            if sig == 0:
                return
            if pd.isna(sl) or pd.isna(tp):
                return

            current_price = self.data.Close[-1]

            if sig == 1 and not self.position.is_long:
                if self.position.is_short:
                    self.position.close()
                self.buy(sl=float(sl), tp=float(tp))

            elif sig == -1 and not self.position.is_short:
                if self.position.is_long:
                    self.position.close()
                self.sell(sl=float(sl), tp=float(tp))

    return DynamicStrategy


def _package_results(df: pd.DataFrame, stats) -> dict:

    # --- candles ---
    # columns are capitalized at this point: Open/High/Low/Close
    candles = []
    for ts, row in df.iterrows():
        candles.append({
            "time":  int(pd.Timestamp(ts).timestamp()),
            "open":  round(float(row["Open"]),  2),
            "high":  round(float(row["High"]),  2),
            "low":   round(float(row["Low"]),   2),
            "close": round(float(row["Close"]), 2),
        })

    # --- signals ---
    signals = []
    for ts, row in df.iterrows():
        sig = row.get("signal", 0)
        sl  = row.get("stop_loss")
        tp  = row.get("take_profit")
        if sig in (1, -1) and not pd.isna(sl) and not pd.isna(tp):
            signals.append({
                "time":   int(pd.Timestamp(ts).timestamp()),
                "type":   "buy" if sig == 1 else "sell",
                "price":  round(float(row["Close"]), 2),
                "stop":   round(float(sl), 2),
                "target": round(float(tp), 2),
            })

    # --- equity curve ---
    equity_curve = []
    eq = stats.get("_equity_curve")
    if eq is not None:
        eq_df = eq.copy()
        eq_df.index = pd.to_datetime(eq_df.index)
        for ts, row in eq_df.iterrows():
            equity_curve.append({
                "time":  int(pd.Timestamp(ts).timestamp()),
                "value": round(float(row["Equity"]), 2),
            })

    # --- trades ---
    trades = []
    trades_df = stats.get("_trades")
    if trades_df is not None and len(trades_df) > 0:
        for _, t in trades_df.tail(20).iterrows():
            pnl_pct = round(float(t.get("ReturnPct", 0)) * 100, 2)
            trades.append({
                "entry_time": str(t.get("EntryTime", "")),
                "exit_time":  str(t.get("ExitTime", "")),
                "type":       "buy" if t.get("Size", 0) > 0 else "sell",
                "entry":      round(float(t.get("EntryPrice", 0)), 2),
                "exit":       round(float(t.get("ExitPrice", 0)), 2),
                "pnl_pct":    pnl_pct,
            })

    # --- metrics ---
    def safe(key, default=0):
        val = stats.get(key, default)
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return default
        return val

    metrics = {
        "return":         round(float(safe("Return [%]")),           2),
        "win_rate":       round(float(safe("Win Rate [%]")),         2),
        "max_drawdown":   round(float(safe("Max. Drawdown [%]")),    2),
        "sharpe":         round(float(safe("Sharpe Ratio")),         2),
        "total_trades":   int(safe("# Trades")),
        "profit_factor":  round(float(safe("Profit Factor")),        2),
        "avg_trade":      round(float(safe("Avg. Trade [%]")),       2),
        "best_trade":     round(float(safe("Best Trade [%]")),       2),
        "worst_trade":    round(float(safe("Worst Trade [%]")),      2),
        "buy_hold":       round(float(safe("Buy & Hold Return [%]")),2),
        "exposure":       round(float(safe("Exposure Time [%]")),    2),
        "start_value":    round(float(safe("Start Value")),          2),
        "end_value":      round(float(safe("End Value")),            2),
    }

    return {
        "candles":      candles,
        "signals":      signals,
        "metrics":      metrics,
        "equity_curve": equity_curve,
        "trades":       trades,
    }