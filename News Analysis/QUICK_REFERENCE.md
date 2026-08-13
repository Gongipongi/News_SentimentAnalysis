# Quick Reference: Stock & Sentiment Plotting

## One-Liner Examples

### View both plots interactively
```bash
python plot_sentiment.py --stock -c Airtel
```

### Save both plots
```bash
python plot_sentiment.py --stock -c Airtel -o sentiment.png --stock-out stock.png
```

### Weekly aggregation
```bash
python plot_sentiment.py --stock -c Airtel -r W
```

### High-resolution plots
```bash
python plot_sentiment.py --stock -c Airtel --dpi 300 -o sentiment_hires.png --stock-out stock_hires.png
```

### Interactive company selection
```bash
python plot_sentiment.py --stock
```

## Key Features

✓ **Automatic Date Alignment**: Stock data spans from earliest news date to latest available
✓ **Separate Visualizations**: Sentiment and stock price in independent graphs
✓ **Company Ticker Mapping**: 10+ built-in company ticker mappings
✓ **Flexible Resampling**: Daily, weekly, or monthly aggregation
✓ **High Quality Output**: Adjustable DPI (200-300+ for publication)
✓ **Database Integration**: Automatically queries your news database

## Command Syntax

```bash
python plot_sentiment.py --stock [OPTIONS]
```

### Options
| Option | Description | Example |
|--------|-------------|---------|
| `-c, --company` | Company name | `-c Airtel` |
| `-r, --resample` | Frequency (D/W/M) | `-r W` |
| `-o, --out` | Sentiment output file | `-o sentiment.png` |
| `--stock-out` | Stock output file | `--stock-out stock.png` |
| `--dpi` | Resolution (int) | `--dpi 300` |

## Date Range Logic

```
News Database           Stock Market Data
├─ Earliest Date ◄──────► START FETCH
│                        │
└─ (Multiple dates)      ├─ [Market data]
                         │
                         ├─ [Market data]
                         │
                         └─ Latest Available ◄──► END FETCH
```

**Result**: Both plots show the same date range (earliest news → latest stock data)

## Stock Ticker Mappings

| Company | Ticker |
|---------|--------|
| Airtel | BHARTIARTL.NS |
| Tesla | TSLA |
| Apple | AAPL |
| Microsoft | MSFT |
| Google | GOOGL |
| Amazon | AMZN |
| Meta | META |
| NVIDIA | NVDA |
| Intel | INTC |
| AMD | AMD |
| IBM | IBM |
| *Others* | `{Company}.NS` (default) |

## Troubleshooting Quick Fixes

| Issue | Fix |
|-------|-----|
| "yfinance is not installed" | `pip install yfinance` |
| "No sentiment data found" | Run `fetch_news.py` first |
| "No stock data found" | Check company name spelling; verify ticker in `get_stock_ticker()` |
| "API rate limited" | Wait a few minutes and retry |

## Example Workflow

```bash
# 1. Fetch news
python fetch_news.py

# 2. View sentim/stock on screen
python plot_sentiment.py --stock -c Airtel

# 3. Save high-quality versions
python plot_sentiment.py --stock -c Airtel --dpi 300 -o sentiment_airtel.png --stock-out stock_airtel.png

# 4. Weekly aggregation
python plot_sentiment.py --stock -c Airtel -r W -o sentiment_weekly.png --stock-out stock_weekly.png
```

## Notes

- Stock data uses company's local currency
- Sentiment ranges: -1 (negative) to +1 (positive)
- Market holidays create gaps in stock data
- Default resampling is daily (D)
- Plots auto-format dates based on range
