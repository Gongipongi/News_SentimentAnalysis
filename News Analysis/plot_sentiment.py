import sqlite3
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.dates as mdates
try:
    import yfinance as yf
except Exception:
    yf = None
from datetime import datetime

DB_PATH = Path(__file__).parent / "news_database.db"


def load_company_df(company, db_path=DB_PATH):
    conn = sqlite3.connect(str(db_path))
    try:
        df = pd.read_sql_query(
            "SELECT published_date, score, roberta_neg, roberta_neut, roberta_pos FROM articles WHERE lower(company) = lower(?)",
            conn,
            params=(company,)
        )
    finally:
        conn.close()

    if df.empty:
        return df

    df['published_date'] = pd.to_datetime(df['published_date'], errors='coerce')
    df = df.dropna(subset=['published_date'])
    df.set_index('published_date', inplace=True)
    return df


def list_companies(db_path=DB_PATH):
    conn = sqlite3.connect(str(db_path))
    try:
        df = pd.read_sql_query("SELECT DISTINCT company FROM articles ORDER BY company", conn)
    finally:
        conn.close()
    if df.empty:
        return []
    return df['company'].dropna().tolist()


def get_earliest_news_date(company, db_path=DB_PATH):
    """Get the earliest published date for a company's news articles."""
    conn = sqlite3.connect(str(db_path))
    try:
        df = pd.read_sql_query(
            "SELECT MIN(published_date) as min_date FROM articles WHERE lower(company) = lower(?)",
            conn,
            params=(company,)
        )
    finally:
        conn.close()
    
    if df.empty or df['min_date'].iloc[0] is None:
        return None
    
    return pd.to_datetime(df['min_date'].iloc[0])


def get_stock_ticker(company, ticker=None):
    """Resolve a stock ticker for the company.
    Prefer an explicit ticker passed by the user; otherwise fall back to a mapping.
    """
    if ticker:
        return ticker.strip()

    ticker_map = {
        'airtel': 'BHARTIARTL.NS',
        'bharti airtel': 'BHARTIARTL.NS',
        'tesla': 'TSLA',
        'apple': 'AAPL',
        'microsoft': 'MSFT',
        'google': 'GOOGL',
        'amazon': 'AMZN',
        'facebook': 'META',
        'meta': 'META',
        'nvidia': 'NVDA',
        'intel': 'INTC',
        'amd': 'AMD',
        'ibm': 'IBM',
        'vodafone idea': 'IDEA.NS',
        'vodafoneidea': 'IDEA.NS',
        'vi': 'IDEA.NS',
        'idea': 'IDEA.NS',
    }
    lookup = company.strip().lower().replace('-', ' ')
    if lookup in ticker_map:
        return ticker_map[lookup]
    return f"{company.strip()}.NS"


def fetch_stock_data(company, start_date=None, end_date=None, ticker=None):
    """Fetch stock data using yfinance for the given company and ticker."""
    if yf is None:
        print("yfinance is not installed. Install it with: pip install yfinance")
        return None
    
    ticker = get_stock_ticker(company, ticker)
    
    if start_date is None:
        start_date = get_earliest_news_date(company)
    
    if start_date is None:
        print(f"No news data found for {company}")
        return None
    
    if end_date is None:
        end_date = datetime.now()
    
    try:
        print(f"Fetching stock data for {ticker} from {start_date.date()} to {end_date.date()}")
        stock_data = yf.download(ticker, start=start_date, end=end_date, progress=False)
        
        if stock_data.empty:
            print(f"No stock data found for ticker {ticker}")
            return None
        
        # Reset index to make date a column
        stock_data = stock_data.reset_index()
        return stock_data
    except Exception as e:
        print(f"Error fetching stock data for {ticker}: {e}")
        return None


def plot_time_series(company, resample='D', save_path=None, show=True, dpi=200):
    df = load_company_df(company)
    if df.empty:
        print(f"No data found for {company}")
        return None

    # If resample is falsy (e.g., '' or None), plot raw per-article scores;
    # otherwise aggregate by the given frequency (daily by default).
    if resample:
        ts = df.resample(resample).mean()
        plot_series = ts['score']
    else:
        ts = df
        plot_series = df['score']

    plt.figure(figsize=(12, 6), dpi=dpi)
    sns.lineplot(data=plot_series, label='Compound score', linewidth=2.2)

    ax = plt.gca()
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(mdates.AutoDateLocator()))
    plt.xticks(rotation=45)

    plt.title(f"Sentiment time series for {company}")
    plt.xlabel("Date")
    plt.ylabel("Score")
    plt.legend()
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, bbox_inches='tight', dpi=dpi)
        print(f"Saved plot to {save_path}")

    if show:
        plt.show()

    plt.close()
    return ts


def plot_sentiment_and_stock(company, resample='D', save_sentiment=None, save_stock=None, show=True, dpi=200, ticker=None):
    """Plot sentiment and stock price on separate graphs for the given company.
    
    The time range is from the earliest published date to the latest stock data available.
    """
    # Load sentiment data
    df_sentiment = load_company_df(company)
    if df_sentiment.empty:
        print(f"No sentiment data found for {company}")
        return None, None
    
    # Get earliest date from news
    earliest_date = df_sentiment.index.min()
    
    # Load stock data
    stock_data = fetch_stock_data(company, start_date=earliest_date, ticker=ticker)
    if stock_data is None or stock_data.empty:
        print(f"No stock data found for {company}. The sentiment graph will still be saved if requested.")
        return None, None
    
    # Convert Date column to datetime and set as index
    stock_data['Date'] = pd.to_datetime(stock_data['Date'])
    stock_data.set_index('Date', inplace=True)
    
    # Resample sentiment data if requested
    if resample:
        ts_sentiment = df_sentiment.resample(resample).mean()
        plot_sentiment_series = ts_sentiment['score']
    else:
        ts_sentiment = df_sentiment
        plot_sentiment_series = df_sentiment['score']
    
    # Create figure 1: Sentiment
    fig1 = plt.figure(figsize=(14, 6), dpi=dpi)
    sns.lineplot(data=plot_sentiment_series, label='Compound score', linewidth=2.2, color='steelblue')
    
    ax = plt.gca()
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(mdates.AutoDateLocator()))
    plt.xticks(rotation=45)
    
    plt.title(f"Sentiment Analysis for {company}")
    plt.xlabel("Date")
    plt.ylabel("Sentiment Score")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    if save_sentiment:
        plt.savefig(save_sentiment, bbox_inches='tight', dpi=dpi)
        print(f"Saved sentiment plot to {save_sentiment}")
    
    # Only show if not saving files
    if show and not save_sentiment:
        plt.show()
    
    plt.close()
    
    # Create figure 2: Stock Price
    fig2 = plt.figure(figsize=(14, 6), dpi=dpi)
    
    # Plot closing price using matplotlib instead of seaborn to avoid multi-index issues
    plt.plot(stock_data.index, stock_data['Close'].values, label='Stock Close Price', linewidth=2.2, color='darkgreen')
    
    ax = plt.gca()
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(mdates.AutoDateLocator()))
    plt.xticks(rotation=45)
    
    plt.title(f"Stock Price for {company}")
    plt.xlabel("Date")
    plt.ylabel("Price")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    if save_stock:
        plt.savefig(save_stock, bbox_inches='tight', dpi=dpi)
        print(f"Saved stock plot to {save_stock}")
    
    # Only show if not saving files
    if show and not save_stock:
        plt.show()
    
    plt.close()
    
    return ts_sentiment, stock_data


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Plot sentiment and stock charts for a company.')
    parser.add_argument('--company', '-c', help='Company name to filter (case-insensitive).')
    parser.add_argument('--ticker', '-t', help='Stock ticker symbol for accurate price data (e.g. BHARTIARTL.NS).')
    parser.add_argument('--resample', '-r', default='D', help='Resample frequency, e.g. D, W, M. Use empty string for raw per-article times.')
    parser.add_argument('--out', '-o', help='Output PNG path for sentiment plot')
    parser.add_argument('--dpi', type=int, default=200, help='DPI for saved PNG')
    parser.add_argument('--stock', action='store_true', help='Generate both sentiment and stock price plots (default behavior).')
    parser.add_argument('--stock-out', help='Output PNG path for stock price plot')
    parser.add_argument('--sentiment-only', action='store_true', help='Generate only the sentiment chart.')
    args = parser.parse_args()

    company = args.company
    ticker = args.ticker

    if not company:
        companies = list_companies()
        if not companies:
            print("No companies found in the database. Please add articles first.")
            raise SystemExit(1)

        print("Available companies in DB:")
        for i, c in enumerate(companies, start=1):
            print(f"{i}. {c}")

        sel = input("Enter company name or number from the list above: ").strip()
        if sel.isdigit():
            idx = int(sel) - 1
            if 0 <= idx < len(companies):
                company = companies[idx]
            else:
                print("Invalid selection number")
                raise SystemExit(1)
        else:
            company = sel

    if not ticker:
        ticker = input(f"Enter stock ticker for {company} (for example BHARTIARTL.NS or IDEA.NS): ").strip()

    if not ticker:
        print("No ticker was entered. The script will still create the sentiment chart, but stock data cannot be fetched without a valid ticker symbol.")
        ticker = None

    if getattr(args, 'sentiment_only', False):
        default_out = f"{company}_sentiment.png"
        resample_arg = args.resample if args.resample != '' else None
        plot_time_series(company, resample=resample_arg, save_path=args.out or default_out, show=False, dpi=args.dpi)
    else:
        default_sentiment = f"{company}_sentiment.png"
        default_stock = f"{company}_stock.png"
        resample_arg = args.resample if args.resample != '' else None
        plot_sentiment_and_stock(
            company,
            resample=resample_arg,
            save_sentiment=args.out or default_sentiment,
            save_stock=args.stock_out or default_stock,
            show=False,
            dpi=args.dpi,
            ticker=ticker,
        )
