import sqlite3
import re
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


def create_daily_sentiment_stock_table(db_path=DB_PATH):
    """Create the aggregate table storing daily average sentiment and daily close prices."""
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_sentiment_stock (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                date TEXT NOT NULL,
                avg_sentiment REAL NOT NULL,
                close_price REAL,
                article_count INTEGER DEFAULT 0,
                UNIQUE(company, date)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_daily_sentiment_stock_company_date ON daily_sentiment_stock(company, date)"
        )
        conn.commit()
    finally:
        conn.close()


def build_daily_sentiment_stock_table(db_path=DB_PATH, company=None):
    """Populate daily_sentiment_stock with one row per company-day.

    Each row stores the mean sentiment score across all articles for that company on that day,
    along with the corresponding daily closing stock price from yfinance.
    """
    create_daily_sentiment_stock_table(db_path)

    conn = sqlite3.connect(str(db_path))
    try:
        if company is None:
            companies = list_companies(db_path)
        else:
            companies = [company]

        for current_company in companies:
            sentiment_df = pd.read_sql_query(
                """
                SELECT date(published_date) AS date, AVG(score) AS avg_sentiment, COUNT(*) AS article_count
                FROM articles
                WHERE lower(company) = lower(?)
                GROUP BY date(published_date)
                ORDER BY date
                """,
                conn,
                params=(current_company,),
            )

            if sentiment_df.empty:
                continue

            sentiment_df['date'] = pd.to_datetime(sentiment_df['date'], errors='coerce').dt.strftime('%Y-%m-%d')
            sentiment_df = sentiment_df.dropna(subset=['date'])
            if sentiment_df.empty:
                continue

            stock_data = fetch_stock_data(
                current_company,
                start_date=sentiment_df['date'].min(),
                end_date=sentiment_df['date'].max(),
                ticker=None,
            )

            if stock_data is not None and not stock_data.empty:
                stock_data = stock_data.copy()
                stock_data['Date'] = pd.to_datetime(stock_data['Date'], errors='coerce').dt.strftime('%Y-%m-%d')
                if 'Close' in stock_data.columns:
                    stock_series = stock_data[['Date', 'Close']].rename(columns={'Close': 'close_price'})
                elif 'Adj Close' in stock_data.columns:
                    stock_series = stock_data[['Date', 'Adj Close']].rename(columns={'Adj Close': 'close_price'})
                else:
                    stock_series = stock_data[['Date', stock_data.columns[-1]]].rename(columns={stock_data.columns[-1]: 'close_price'})
                stock_series = stock_series.dropna(subset=['Date'])
            else:
                stock_series = pd.DataFrame(columns=['Date', 'close_price'])

            merged = sentiment_df.merge(stock_series, left_on='date', right_on='Date', how='left')
            merged = merged[['date', 'avg_sentiment', 'article_count', 'close_price']].copy()
            merged['company'] = current_company
            merged = merged[['company', 'date', 'avg_sentiment', 'close_price', 'article_count']]

            if merged.empty:
                continue

            conn.execute(
                "DELETE FROM daily_sentiment_stock WHERE lower(company) = lower(?)",
                (current_company,),
            )

            for record in merged.to_dict(orient='records'):
                close_price = record.get('close_price')
                if pd.isna(close_price):
                    close_price = None
                else:
                    close_price = float(close_price)

                conn.execute(
                    """
                    INSERT INTO daily_sentiment_stock (company, date, avg_sentiment, close_price, article_count)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(company, date) DO UPDATE SET
                        avg_sentiment = excluded.avg_sentiment,
                        close_price = excluded.close_price,
                        article_count = excluded.article_count
                    """,
                    (
                        record['company'],
                        record['date'],
                        float(record['avg_sentiment']),
                        close_price,
                        int(record['article_count']),
                    ),
                )

        conn.commit()
    finally:
        conn.close()


def load_daily_sentiment_stock(company=None, db_path=DB_PATH):
    """Return the daily aggregate table for one company or the full table."""
    conn = sqlite3.connect(str(db_path))
    try:
        if company:
            df = pd.read_sql_query(
                "SELECT company, date, avg_sentiment, close_price, article_count FROM daily_sentiment_stock WHERE lower(company) = lower(?) ORDER BY date",
                conn,
                params=(company,),
            )
        else:
            df = pd.read_sql_query(
                "SELECT company, date, avg_sentiment, close_price, article_count FROM daily_sentiment_stock ORDER BY company, date",
                conn,
            )
    finally:
        conn.close()

    if df.empty:
        return df

    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    return df


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
        'coal india': 'COALINDIA.NS',
        'coalindia': 'COALINDIA.NS',
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
        'hpcl': 'HINDPETRO.NS',
        'hindustan petroleum': 'HINDPETRO.NS',
        'hindustan petroleum corporation': 'HINDPETRO.NS',
        'hindpetro': 'HINDPETRO.NS',
    }
    lookup = company.strip().lower().replace('-', ' ')
    if lookup in ticker_map:
        return ticker_map[lookup]

    sanitized = re.sub(r'[^A-Za-z0-9]+', '', company.strip()).upper()
    return f"{sanitized}.NS"


def fetch_stock_data(company, start_date=None, end_date=None, ticker=None):
    """Fetch stock data using yfinance for the given company and ticker."""
    if yf is None:
        print("yfinance is not installed. Install it with: pip install yfinance")
        return None

    ticker = get_stock_ticker(company, ticker).strip()
    if " " in ticker and ticker.lower().endswith(('.ns', '.bo', '.nse', '.bom')):
        ticker = ticker.replace(' ', '')

    if start_date is None:
        start_date = get_earliest_news_date(company)

    if start_date is None:
        print(f"No news data found for {company}")
        return None

    if end_date is None:
        end_date = datetime.now()

    start_ts = pd.Timestamp(start_date)
    end_ts = pd.Timestamp(end_date)

    try:
        print(f"Fetching stock data for {ticker} from {start_ts.date()} to {end_ts.date()}")
        stock_data = yf.download(ticker, start=start_ts, end=end_ts, progress=False)

        if stock_data.empty:
            print(f"No stock data found for ticker {ticker}")
            return None

        # Reset index to make date a column
        stock_data = stock_data.reset_index()
        if isinstance(stock_data.columns, pd.MultiIndex):
            stock_data.columns = [col[0] if isinstance(col, tuple) else col for col in stock_data.columns]
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
    """Plot sentiment and stock price in a single combined figure for the given company.

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

    plot_sentiment_series = plot_sentiment_series.copy()
    plot_sentiment_series.name = 'sentiment'

    if 'Close' in stock_data.columns:
        stock_series = stock_data['Close'].copy()
    elif 'Adj Close' in stock_data.columns:
        stock_series = stock_data['Adj Close'].copy()
    else:
        stock_series = stock_data.iloc[:, -1].copy()
    stock_series.name = 'close_price'

    combined = pd.concat([plot_sentiment_series, stock_series], axis=1, join='inner')
    if combined.empty:
        print(f"No overlapping sentiment and stock data found for {company}.")
        return ts_sentiment, stock_data

    fig, ax1 = plt.subplots(figsize=(14, 6), dpi=dpi)
    sns.lineplot(data=combined['sentiment'], ax=ax1, label='Compound score', linewidth=2.2, color='steelblue')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Sentiment Score', color='steelblue')
    ax1.tick_params(axis='y', labelcolor='steelblue')
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax1.xaxis.set_major_formatter(mdates.ConciseDateFormatter(mdates.AutoDateLocator()))
    plt.xticks(rotation=45)

    ax2 = ax1.twinx()
    ax2.plot(combined.index, combined['close_price'], label='Stock Close Price', linewidth=2.2, color='darkgreen')
    ax2.set_ylabel('Price', color='darkgreen')
    ax2.tick_params(axis='y', labelcolor='darkgreen')

    handles1, labels1 = ax1.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(handles1 + handles2, labels1 + labels2, loc='upper left')

    plt.title(f"{company} sentiment vs stock price")
    plt.tight_layout()

    output_path = save_sentiment or save_stock
    if output_path:
        plt.savefig(output_path, bbox_inches='tight', dpi=dpi)
        print(f"Saved combined sentiment/stock plot to {output_path}")

    if show and not output_path:
        plt.show()

    plt.close(fig)
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
        default_combined = f"{company}_sentiment_stock.png"
        resample_arg = args.resample if args.resample != '' else None
        output_path = args.out or args.stock_out or default_combined
        plot_sentiment_and_stock(
            company,
            resample=resample_arg,
            save_sentiment=output_path,
            save_stock=None,
            show=False,
            dpi=args.dpi,
            ticker=ticker,
        )
