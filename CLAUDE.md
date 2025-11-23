# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**No29_stock_auto** is an automated Japanese stock screening and backtesting system that identifies trading opportunities in Nikkei 225 and Tokyo Stock Exchange Prime Market stocks. It uses three complementary trading strategies with full historical validation and daily signal generation.

## Quick Start Commands

### Daily Screening (Find today's signals)
```bash
# Default strategies from config.py
python -m src.main

# Specific strategies
python -m src.main --strategies original
python -m src.main --strategies original momentum_breakout
python -m src.main --strategies all

# Refresh data from API (ignore cache)
python -m src.main --refresh
```
**Output**: `recommendations_YYYYMMDD.csv` with buy signals, entry/TP/SL prices

### Backtesting (Historical validation, past 2 years)
```bash
# Single strategy
python -m src.backtest --strategies original

# Multi-strategy combination
python -m src.backtest --strategies original momentum_breakout

# Compare all possible combinations automatically
python -m src.backtest --compare

# Custom investment per trade
python -m src.backtest --strategies all --investment 5000000

# Refresh data
python -m src.backtest --strategies all --refresh
```
**Output**: Console metrics + CSV in `backtest_results/`

### Setup & Dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Architecture Overview

The system follows a **modular pipeline architecture**:

```
Data Acquisition → Indicator Calculation → Signal Detection → Backtesting
(yfinance/cache)   (custom TA library)     (3 strategies)    (OHLC simulator)
```

### Key Components

| Component | File | Purpose |
|-----------|------|---------|
| **Data Loading** | `src/data_loader.py` | Fetch/cache data from yfinance, manage ~13 MB local cache |
| **Indicators** | `src/indicators.py` | Custom TA library (SMA, RSI, ATR, ADX, MACD, Bollinger Bands) |
| **Signal Detection** | `src/screener.py` | Strategy logic & entry/exit rules for 3 strategies |
| **Daily Screening** | `src/main.py` | CLI entry point for live signal generation |
| **Backtesting** | `src/backtest.py` | Day-by-day trade simulation & performance metrics |
| **Configuration** | `src/config.py` | Strategy parameters, ticker list (304 stocks), thresholds |

### The Three Trading Strategies

All strategies filter for: price > 75-day SMA, liquidity ≥ 1B JPY daily turnover

#### 1. **Overnight Dip Sniper** (original)
- **Profile**: Mean reversion / dip buying (medium risk/reward, win-rate focused)
- **Entry**: RSI 25-50, ADX ≥ 20, Volume ≥ 1.0x avg, 25-day SMA rising
- **Exit**: TP = Entry + ATR×2.0, SL = Entry - ATR×1.0, Time Stop = 3 days

#### 2. **Momentum Breakout** (momentum_breakout)
- **Profile**: Trend continuation (high risk/reward, trend-following)
- **Entry**: RSI 60-80, ADX ≥ 30, Volume ≥ 1.2x avg, Price > Bollinger Band upper, Breaking 20-day high
- **Exit**: TP = Entry + ATR×3.0, SL = Entry - ATR×1.0, Time Stop = 2 days

#### 3. **Volume Climax Reversal** (volume_climax)
- **Profile**: Panic reversal (low risk, high win-rate, quick rebounds)
- **Entry**: RSI < 30, Volume ≥ 1.5x avg, Price within 10% of 60-day low, MACD histogram turning up
- **Exit**: TP = Entry + ATR×2.5, SL = Entry - ATR×1.0, Time Stop = 2 days

### Data Flow

**Screening Flow**:
1. Load 304 tickers from `config.py`
2. Fetch 1 year history (cached in `data_cache/{ticker}_{period}.csv`)
3. Add all 10+ indicators to daily candles
4. Check all 3 strategies independently
5. Output CSV with signals, entry/TP/SL prices for IFD-OCO orders

**Backtest Flow**:
1. Fetch 2 years history for 304 stocks
2. Simulate day-by-day: check entry signals, manage active trades, record exits
3. Compare multiple strategy combinations automatically
4. Output: trade-by-trade results + performance metrics

### Caching Strategy

- **Local filesystem cache** in `data_cache/` (~13 MB) reduces API calls from hours to minutes
- Cache key format: `{ticker}_{period}.csv` (e.g., `6758.T_1y.csv`)
- Use `--refresh` flag to force fresh data from yfinance

## Critical Design Decisions

### 1. ATR-Based Risk Management
- TP/SL adapts to **volatility** (ATR multipliers), not fixed percentages
- Enables consistent risk-reward ratios across 304 different price levels

### 2. Trade Execution Order (Conservative)
- **SL checked BEFORE TP** when simulating next-day OHLC
- Prevents unrealistic "escaped SL" scenarios in backtests
- No slippage assumptions (use next-day open/high/low/close exactly)

### 3. Market Filter
- **Nikkei 225 SMA(75) uptrend filter** applied in backtests
- Signals only during market uptrend conditions, reducing false signals

### 4. Multi-Strategy Isolation
- Each strategy maintains **separate active trades** per stock
- Can combine 1, 2, or all 3 with `--strategies` or `--compare`

### 5. Custom TA Library
- Lightweight implementations replace pandas_ta dependency
- All indicators computed using rolling windows on pandas Series

## Configuration (src/config.py)

### Strategy Selection
```python
ACTIVE_STRATEGIES = ['original']  # Default; override via CLI
```

### Key Thresholds by Strategy
| Parameter | Original | Momentum | Volume |
|-----------|----------|----------|--------|
| RSI Range | 25-50 | 60-80 | <30 |
| ADX Min | 20 | 30 | N/A |
| Volume Mult | 1.0x | 1.2x | 1.5x |
| TP (ATR) | 2.0x | 3.0x | 2.5x |
| SL (ATR) | 1.0x | 1.0x | 1.0x |
| Time Stop | 3 days | 2 days | 2 days |

**Target Universe**: 304 stocks (Nikkei 225 + major Tokyo Stock Exchange Prime stocks), all with `.T` ticker suffix

## Recent Performance (2-year backtest)

| Metric | Original | Momentum | Volume | All 3 Combined |
|--------|----------|----------|--------|----------------|
| Total Trades | 120 | ~80 | ~40 | 267 |
| Win Rate | 50.0% | ~52% | ~55% | 51.31% |
| Avg Profit/Trade | 0.39% | ~0.52% | ~0.48% | 0.49% |
| Total Return | 47.16% | ~54% | ~38% | 130.83% |

## Coding Standards & Rules

This repository follows established coding guidelines from `.claude/rules/`:

- **coding.md (v5)**: Task classification (lightweight/standard/critical), tool usage, reasoning depth
- **test-strategy.md**: Test perspectives table with equivalence partitioning, GWT format, 100% branch coverage target

When implementing features or fixes:
1. Classify the task (lightweight = quick fix, standard = multi-file changes, critical = auth/schema/infrastructure)
2. Read relevant files before proposing changes
3. For non-trivial tests, create a test perspectives table first covering normal/abnormal/boundary cases
4. Use GWT comment format (Given/When/Then) in test code
5. Aim for 100% branch coverage on new/modified code

## Common Development Tasks

### Add a new indicator
1. Implement in `src/indicators.py` using pandas rolling windows
2. Call it in `src/screener.add_indicators()`
3. Reference in strategy check functions
4. Document in README.md and update parameters in `config.py`

### Modify strategy parameters
1. Edit thresholds in `src/config.py` (e.g., `RSI_LOWER = 25`)
2. Run backtest: `python -m src.backtest --strategies original --compare`
3. Validate via console output or `backtest_results/` CSV
4. Update expected performance in README.md

### Extend to new stocks
1. Add ticker (must use `.T` format) to `PRIME_TICKERS` in `config.py`
2. System fetches data automatically on next run
3. Cache populates in `data_cache/`

### Debug a signal
1. Run screening: `python -m src.main --strategies original`
2. Check output CSV for stock details (RSI, ADX, ATR)
3. Manually verify calculations with historical data
4. Adjust thresholds in `config.py` if needed
5. Re-run backtest to validate changes

## File Structure

```
src/
├── main.py           # Daily screening CLI entry point (96 lines)
├── backtest.py       # Backtesting engine (482 lines)
├── screener.py       # Strategy signal detection (346 lines)
├── config.py         # Parameters & ticker list (91 lines)
├── data_loader.py    # yfinance + caching (83 lines)
└── indicators.py     # Custom TA indicators (89 lines)

data_cache/          # Local OHLC cache (~13 MB)
backtest_results/    # Backtest output CSVs
.claude/rules/       # Coding & testing guidelines
```

## Key Technical Indicators

All computed daily using pandas rolling windows:

| Indicator | Purpose | Periods |
|-----------|---------|---------|
| SMA | Trend identification | 25, 75 days |
| RSI | Momentum/overbought | 14 |
| ATR | Volatility-based stops | 14 |
| ADX | Trend strength | 14 |
| Bollinger Bands | Breakout detection | 20, σ=2 |
| MACD | Reversal confirmation | 12/26/9 |
| Volume SMA | Surge detection | 20 |

## Data Source & Caching

- **Source**: Yahoo Finance API via yfinance
- **Update Frequency**: Daily (1D candles)
- **Screening Data**: 1 year history per stock
- **Backtest Data**: 2 years history per stock
- **Cache Format**: CSV in `data_cache/{ticker}_{period}.csv`
- **Cache Refresh**: Manual via `--refresh` flag

## Version History

- **v3.0 (2025)**: Multi-strategy system, combination backtesting, custom TA library
- **v2.0 (2024)**: ATR-based risk management, RSI optimization, ADX filter
- **v1.0 (Initial)**: Basic dip-buying with fixed %-based stops

---

## When Uncertain

- See README.md for full strategy details and output examples
- See CACHING.md for architecture of data caching system
- Check `.claude/rules/` for coding standards and test design patterns
- Refer to recent commits for implementation examples
