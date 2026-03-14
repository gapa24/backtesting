import os
import traceback
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.data_loader import load_data
from app.backtest_runner import run_backtest

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="Backtester", version="1.0.0")

BASE_DIR    = Path(__file__).parent
STATIC_DIR = BASE_DIR.parent / "static"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class BacktestRequest(BaseModel):
    code:     str
    interval: str   # "1min" | "5min" | "10min" | "15min" | "30min"
    period:   str   # "full" | "60d"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
def serve_frontend():
    """Serve the single-page frontend."""
    index = STATIC_DIR / "index.html"
    if not index.exists():
        raise HTTPException(status_code=404, detail="index.html not found in /static")
    return FileResponse(index)


@app.get("/health")
def health():
    """Simple health check — useful for Render to confirm the app is up."""
    return {"status": "ok"}


@app.post("/backtest")
def backtest(req: BacktestRequest):
    """
    Main endpoint.

    Receives strategy code + config, runs the backtest,
    returns chart data + metrics as JSON.
    """

    # --- validate interval ---
    allowed_intervals = {"1min", "3min", "5min", "10min", "15min", "30min"}
    if req.interval not in allowed_intervals:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid interval '{req.interval}'. Allowed: {sorted(allowed_intervals)}"
        )

    # --- validate period ---
    allowed_periods = {"full", "60d"}
    if req.period not in allowed_periods:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid period '{req.period}'. Allowed: {sorted(allowed_periods)}"
        )

    # --- validate code is not empty ---
    if not req.code or not req.code.strip():
        raise HTTPException(status_code=400, detail="Strategy code cannot be empty.")

    # --- load data ---
    try:
        df = load_data(req.interval, req.period)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load data: {str(e)}"
        )

    if df.empty:
        raise HTTPException(
            status_code=404,
            detail="No data returned for the selected interval and period."
        )

    # --- run backtest ---
    try:
        result = run_backtest(req.code, df)
    except ValueError as e:
        # user error — bad code, missing function, blocked keyword etc.
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Backtest failed: {str(e)}\n{traceback.format_exc()}"
        )

    return result


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    import os 

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        reload=True,
    )
