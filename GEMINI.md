# Multi-Strategy Trading System

This is a Python-based trading system designed for the Japanese stock market (Tokyo Stock Exchange Prime / Nikkei 225). It implements multiple trading strategies to identify buy signals, perform backtests, and optimize trading portfolios.

## Project Overview

The system scans approximately 300+ major Japanese stocks to find trading opportunities based on technical analysis. It supports three distinct strategies:

1.  **Overnight Dip Sniper (Original):** A mean-reversion strategy targeting short-term dips in an uptrend.
2.  **Momentum Breakout:** A trend-following strategy catching strong upward momentum and breakouts.
3.  **Volume Climax Reversal:** A reversal strategy targeting panic selling bottoms (currently experimental).

The core philosophy is to use algorithmic, emotion-free logic to generate "IFD-OCO" (If Done - One Cancels Other) orders for the next trading day.

## Key Components

*   **`src/main.py`**: The entry point for daily stock screening. It fetches the latest data, applies the active strategies, and outputs a list of recommended trades with entry, take-profit, and stop-loss prices.
*   **`src/backtest.py`**: A robust backtesting engine that simulates trading performance over the past 2 years. It supports strategy comparison (`--compare`) to find the best-performing combination.
*   **`src/screener.py`**: Contains the core logic for technical indicators and signal detection for each strategy.
*   **`src/config.py`**: Central configuration file for strategy parameters (RSI thresholds, ATR multipliers, moving averages) and the target ticker list.
*   **`src/data_loader.py`**: Handles data fetching from Yahoo Finance (`yfinance`) and local caching to speed up repeated runs.

## Building and Running

### Prerequisites

- Python 3.x
- Virtual environment (recommended)

### Setup

1.  **Initialize Environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # macOS/Linux
    # venv\Scripts\activate  # Windows
    ```

2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### Usage Commands

**1. Daily Signal Screening**
Run this after the market closes to generate signals for the next day.
```bash
# Run with default active strategies
python -m src.main

# Run with specific strategies
python -m src.main --strategies original momentum_breakout
```

**2. Backtesting**
Verify strategy performance using historical data.
```bash
# Run backtest for specific strategies
python -m src.backtest --strategies original

# Compare all strategy combinations to find the best portfolio
python -m src.backtest --compare
```

**3. Configuration**
Edit `src/config.py` to adjust:
- `ACTIVE_STRATEGIES`: Default strategies to run.
- `PRIME_TICKERS`: List of stock symbols to scan.
- Strategy parameters (e.g., `RSI_LOWER`, `ATR_MULTIPLIER_TP`).

## Development Conventions

*   **Modular Design:** Logic is separated into data loading, screening, and execution (main/backtest).
*   **Type Hinting:** Python type hints are used for clarity.
*   **Data Caching:** Historical data is cached in `data_cache/` to reduce API calls. Use `--refresh` flag to force an update.
*   **Strategy Pattern:** New strategies should be implemented as separate functions in `src/screener.py` (e.g., `check_signal_new_strategy`) and integrated into `check_signal`.
