# backtest_project

A lightweight Python backtesting project for analyzing historical stock/index price data.

## 📦 Project Structure

- `src/` - Main application source code
  - `backtest_runner.py` - Core backtesting logic
  - `data_loader.py` - Data loading and preprocessing utilities
  - `main.py` - Entry point for running the backtest
  - `render.yaml` - Rendering configuration used by the app
  - `static/index.html` - Optional static view for rendered output
- `data/` - Sample CSV price history files (NIFTY 50 in several timeframes)
- `test/` - Unit tests

## 🚀 Getting Started

### 1) Create a virtual environment (recommended)

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies

```bash
pip install -r src/requirements.txt
```

## ▶️ Running the Backtest

From the project root:

```bash
python -m src.main
```

This will load the sample data files from `data/` and execute the backtest logic.

## 🧪 Running Tests

From the project root:

```bash
python -m test.testing
```

## 📁 Data Files

The `data/` folder contains sample CSV files for the NIFTY 50 index at different timeframes:
- `NIFTY 50_minute.csv`
- `NIFTY 50_5minute.csv`
- `NIFTY 50_15minute.csv`

## 🔧 Notes / Customization

- Update/replace the CSV files in `data/` with your own historical price data.
- Modify the logic in `src/backtest_runner.py` to change strategy rules, risk parameters, or reporting.

---

If you want help extending the strategy (entry/exit rules, indicator calculation, reporting, or visualization), just ask!