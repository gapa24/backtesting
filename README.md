# NIFTY 50 Backtester

A web-based backtesting platform for testing trading strategies on NIFTY 50 historical data. Built with FastAPI, featuring a clean web interface for strategy development and visualization.

## 📁 Project Structure

```
backtest_project/
├── app/                          # Main application code
│   ├── __init__.py
│   ├── main.py                   # FastAPI app with routes
│   ├── data_loader.py            # Data loading from CSV/yfinance
│   └── backtest_runner.py        # Backtesting logic & safety checks
├── data/                         # Historical price data (CSV files)
│   ├── NIFTY 50_minute_2023_2025.csv
│   ├── NIFTY 50_5minute_2023_2025.csv
│   └── NIFTY 50_15minute_2023_2025.csv
├── static/                       # Frontend assets
│   └── index.html                # Single-page web interface
├── test/                         # Unit tests
│   ├── __init__.py
│   └── testing.py                # Test cases for data loading & backtesting
├── render.yaml                   # Deployment config for Render
├── requirements.txt              # Python dependencies
├── .gitignore                    # Git ignore rules
├── .python-version               # Python version specification
└── LICENSE                       # Project license
```

## 🚀 Getting Started

### Prerequisites
- Python 3.12+
- pip for package management

### 1. Clone & Setup Environment

```bash
git clone <your-repo-url>
cd backtest_project
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the Application

```bash
python -m app.main
```

The app will start on `http://localhost:8000`. Open this URL in your browser to access the web interface.

## 🧪 Running Tests

```bash
python -m test.testing
```

## 📊 How It Works: Code Workflow for Juniors

This section explains the step-by-step flow of how the backtester processes your trading strategy.

### 1. **User Input (Frontend)**
- You write Python code defining a `generate_signals()` function in the web interface
- Select timeframe (1min, 5min, 15min, etc.) and period (full history or last 60 days)
- Click "Run Backtest"

### 2. **Data Loading (`app/data_loader.py`)**
```python
# Example: Load 15-minute NIFTY 50 data
df = load_data("15min", "full")  # Returns OHLCV DataFrame
```
- **Full period**: Loads from local CSV files in `/data/`
- **60d period**: Fetches recent data from Yahoo Finance
- Data is cleaned and filtered to NSE market hours (9:15 AM - 3:29 PM IST)

### 3. **Strategy Execution (`app/backtest_runner.py`)**
```python
# Your strategy code is executed safely
def generate_signals(df):
    # Add technical indicators
    df['sma'] = ta.sma(df['Close'], length=20)

    # Generate buy/sell signals (-1, 0, 1)
    df['signal'] = 0  # 0=hold, 1=buy, -1=sell
    df['stop_loss'] = None
    df['take_profit'] = None

    # Example: Buy when price > SMA
    buy_condition = df['Close'] > df['sma']
    df.loc[buy_condition, 'signal'] = 1
    df.loc[buy_condition, 'stop_loss'] = df['Low'] * 0.98   # 2% stop loss
    df.loc[buy_condition, 'take_profit'] = df['Close'] * 1.05  # 5% target

    return df
```

### 4. **Backtesting Engine**
- Uses the `backtesting.py` library to simulate trades
- Applies your signals with stop-loss and take-profit levels
- Calculates realistic NSE commissions (0.02% per trade)
- Tracks equity curve and performance metrics

### 5. **Results Visualization**
- **Candlestick Chart**: Shows price action with your signals overlaid
- **Equity Curve**: Portfolio value over time
- **Performance Metrics**: Win rate, Sharpe ratio, max drawdown, etc.
- **Trade Log**: List of executed trades with P&L

## 📝 Writing Your First Strategy

Here's a simple moving average crossover strategy:

```python
import pandas_ta as ta

def generate_signals(df):
    # Calculate indicators
    df['fast_sma'] = ta.sma(df['Close'], length=9)
    df['slow_sma'] = ta.sma(df['Close'], length=21)

    # Initialize signal columns
    df['signal'] = 0
    df['stop_loss'] = None
    df['take_profit'] = None

    # Buy when fast SMA crosses above slow SMA
    buy_signal = (df['fast_sma'] > df['slow_sma']) & (df['fast_sma'].shift(1) <= df['slow_sma'].shift(1))
    df.loc[buy_signal, 'signal'] = 1
    df.loc[buy_signal, 'stop_loss'] = df['Low'] * 0.97    # 3% stop loss
    df.loc[buy_signal, 'take_profit'] = df['Close'] * 1.10  # 10% target

    # Sell when fast SMA crosses below slow SMA
    sell_signal = (df['fast_sma'] < df['slow_sma']) & (df['fast_sma'].shift(1) >= df['slow_sma'].shift(1))
    df.loc[sell_signal, 'signal'] = -1
    df.loc[sell_signal, 'stop_loss'] = df['High'] * 1.03   # 3% stop loss
    df.loc[sell_signal, 'take_profit'] = df['Close'] * 0.90  # 10% target

    return df
```

## 🔒 Security Features

- **Code Sandboxing**: Dangerous operations (file access, network calls, etc.) are blocked
- **Input Validation**: Strategy code is checked for syntax and required functions
- **Safe Execution**: User code runs in isolated environment

## 🚀 Deployment

The app is configured for deployment on Render.com:

```bash
# Build command: pip install -r requirements.txt
# Start command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## 📋 API Endpoints

- `GET /` - Serve web interface
- `GET /health` - Health check
- `POST /backtest` - Run backtest with strategy code

## 🛠️ Customization

- **Add New Indicators**: Use `pandas-ta` library in your strategy
- **Change Data Source**: Modify `app/data_loader.py` for different assets
- **Adjust Commissions**: Update commission rate in `app/backtest_runner.py`
- **Add Risk Management**: Extend stop-loss/take-profit logic

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

---

Happy backtesting! 📈