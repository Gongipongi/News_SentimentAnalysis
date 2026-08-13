# Stock Price & Sentiment Analysis Integration Guide

## Overview
This guide explains how to use the new stock price and sentiment analysis visualization feature in your news analysis project.

## What's New
The `plot_sentiment.py` script now includes functionality to:
- **Fetch stock data** using yfinance for any company
- **Automatically determine date range** from the earliest news publication to the latest available stock data
- **Generate separate visualizations** for sentiment analysis and stock prices
- **Automatic ticker mapping** for common companies

## Installation
yfinance has been installed and is ready to use. If you need to reinstall it later:
```bash
pip install yfinance
```

## Usage

### Basic Usage - Interactive Mode
```bash
python plot_sentiment.py --stock
```
This will prompt you to select a company from the database, then generate both sentiment and stock price plots.

### Specify Company
```bash
python plot_sentiment.py --stock -c Airtel
```

### Save Plots to Files
```bash
python plot_sentiment.py --stock -c Airtel -o sentiment.png --stock-out stock.png
```

### Adjust Resampling Frequency
By default, plots use daily (D) resampling. You can change this:
- **Daily**: `-r D` (default)
- **Weekly**: `-r W`
- **Monthly**: `-r M`

Example with weekly resampling:
```bash
python plot_sentiment.py --stock -c Airtel -r W
```

### Set Custom DPI for Higher Resolution
```bash
python plot_sentiment.py --stock -c Airtel --dpi 300
```

## How It Works

### 1. Date Range Determination
- The script queries your news database to find the **earliest published date**
- Stock data is fetched from that earliest date to the **latest available data** from yfinance
- This ensures your sentiment and stock data cover the same time period

### 2. Ticker Symbol Resolution
The script includes a built-in mapping of company names to stock tickers:
- **Airtel** → `BHARTIARTL.NS` (India NSE)
- **Tesla** → `TSLA`
- **Apple** → `AAPL`
- **Microsoft** → `MSFT`
- **Google** → `GOOGL`
- **Amazon** → `AMZN`
- **Meta** → `META`
- **NVIDIA** → `NVDA`
- **Intel** → `INTC`
- **AMD** → `AMD`
- **IBM** → `IBM`

For unmapped companies, the default format is: `{CompanyName}.NS` (Indian NSE ticker)

### 3. Visualization
Two separate plots are generated:

#### Plot 1: Sentiment Analysis
- Shows the compound sentiment score over time
- Blue line indicating sentiment trends
- Grid for easy reading
- X-axis shows dates with automatic formatting

#### Plot 2: Stock Price
- Shows closing stock price over time
- Green line indicating price trends
- Grid for easy reading
- X-axis shows dates with automatic formatting

## Output

### Plot Elements
- **Title**: Clearly indicates what is being shown
- **X-axis**: Date range (from earliest news to latest stock data)
- **Y-axis**: Sentiment Score (for sentiment) or Stock Price (for stock)
- **Legend**: Labels for each line
- **Grid**: Helps reading values
- **Size**: 14x6 inches by default (can be adjusted)

### File Output
When using `-o` and `--stock-out` options, plots are saved as PNG files with:
- Default DPI: 200
- Custom DPI: Use `--dpi` parameter (e.g., `--dpi 300` for higher quality)

## Example Commands

### Scenario 1: Quick visualization
```bash
python plot_sentiment.py --stock -c Airtel
```

### Scenario 2: Generate high-resolution publication-ready plots
```bash
python plot_sentiment.py --stock -c Airtel -o sentiment_airtel.png --stock-out stock_airtel.png --dpi 300
```

### Scenario 3: Weekly aggregation with saved files
```bash
python plot_sentiment.py --stock -c Airtel -r W -o sentiment_weekly.png --stock-out stock_weekly.png
```

### Scenario 4: Interactive company selection
```bash
python plot_sentiment.py --stock
# Then select from the list of available companies
```

## Troubleshooting

### Issue: "yfinance is not installed"
**Solution**: Run `pip install yfinance`

### Issue: No stock data retrieved
**Possible causes**:
1. **Incorrect ticker symbol**: The company name might not be in the predefined mapping
   - **Solution**: Edit `get_stock_ticker()` function in `plot_sentiment.py` to add your company's ticker
   
2. **API rate limiting**: yfinance might be rate-limited
   - **Solution**: Wait a few moments and try again
   
3. **No data for date range**: The ticker might not have data for the dates in your news database
   - **Solution**: Check if the ticker symbol is correct using yfinance documentation

### Issue: "No sentiment data found"
**Solution**: Make sure you have run `fetch_news.py` first to populate the database with news articles

## Adding New Company Tickers

To add support for a company not in the predefined list, edit the `get_stock_ticker()` function in `plot_sentiment.py`:

```python
def get_stock_ticker(company):
    """Map company name to stock ticker symbol."""
    ticker_map = {
        'Airtel': 'BHARTIARTL.NS',
        'Tesla': 'TSLA',
        'YourCompany': 'TICKER',  # Add your company here
        # ... rest of mappings
    }
    return ticker_map.get(company.strip(), f"{company}.NS")
```

Replace:
- `'YourCompany'` with your company name (as it appears in the database)
- `'TICKER'` with the actual stock ticker symbol

## Advanced Features

### Accessing Raw Data Programmatically
You can use the functions in `plot_sentiment.py` directly in your code:

```python
from plot_sentiment import (
    get_earliest_news_date,
    fetch_stock_data,
    load_company_df
)

# Get earliest date
earliest = get_earliest_news_date('Airtel')

# Fetch stock data
stock_df = fetch_stock_data('Airtel', start_date=earliest)

# Load sentiment data
sentiment_df = load_company_df('Airtel')

# Now you can analyze or plot them as needed
```

### Custom Date Range
```python
from datetime import datetime
from plot_sentiment import fetch_stock_data

# Fetch stock data for a specific date range
stock_df = fetch_stock_data(
    'Airtel',
    start_date=datetime(2026, 8, 1),
    end_date=datetime(2026, 8, 31)
)
```

## Technical Details

### Functions Added

1. **`get_earliest_news_date(company, db_path)`**
   - Returns the earliest published date for a company's news articles
   - Parameters:
     - `company`: Company name (case-insensitive)
     - `db_path`: Path to database (default: current directory)
   - Returns: pandas Timestamp or None

2. **`get_stock_ticker(company)`**
   - Maps company name to stock ticker symbol
   - Parameters:
     - `company`: Company name
   - Returns: Stock ticker string (e.g., 'BHARTIARTL.NS')

3. **`fetch_stock_data(company, start_date, end_date)`**
   - Fetches stock data using yfinance
   - Parameters:
     - `company`: Company name
     - `start_date`: Start date (default: earliest news date)
     - `end_date`: End date (default: today)
   - Returns: pandas DataFrame with stock data or None

4. **`plot_sentiment_and_stock(company, resample, save_sentiment, save_stock, show, dpi)`**
   - Creates separate sentiment and stock price plots
   - Parameters:
     - `company`: Company name
     - `resample`: Resample frequency ('D', 'W', 'M', or None)
     - `save_sentiment`: Path to save sentiment plot PNG
     - `save_stock`: Path to save stock plot PNG
     - `show`: Whether to display plots (default: True)
     - `dpi`: Resolution (default: 200)
   - Returns: Tuple of (sentiment_df, stock_df)

## Dependencies

- **yfinance**: Stock data fetching (now installed)
- **pandas**: Data manipulation
- **matplotlib**: Plotting
- **seaborn**: Enhanced plotting
- **sqlite3**: Database access

All dependencies are already installed in your Python environment.

## Notes

- The earliest news date determines the start of the stock data fetch
- Stock market holidays may result in gaps in the data
- Stock prices are in the currency of the stock exchange (INR for BHARTIARTL.NS, USD for US stocks, etc.)
- Sentiment scores range from -1 (most negative) to +1 (most positive)

## Contact & Support

For issues with yfinance or stock data, refer to the [yfinance GitHub repository](https://github.com/ranaroussi/yfinance)

For issues with sentiment analysis, check the database and ensure `fetch_news.py` has been run successfully.
