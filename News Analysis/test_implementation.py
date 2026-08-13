#!/usr/bin/env python
"""Test script to verify stock and sentiment integration."""

import sqlite3
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from plot_sentiment import (
    get_earliest_news_date, 
    get_stock_ticker, 
    fetch_stock_data,
    list_companies
)

DB_PATH = Path(__file__).parent / "news_database.db"

print("=" * 60)
print("Testing Stock Price & Sentiment Integration")
print("=" * 60)

# Check database
conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()
cursor.execute('SELECT COUNT(DISTINCT company) as cnt FROM articles')
result = cursor.fetchone()
print(f"\n✓ Companies in database: {result[0]}")

companies = list_companies()
print("\nAvailable companies:")
for company in companies:
    print(f"  - {company}")

# Test with first company
if companies:
    test_company = companies[0]
    print(f"\n{'=' * 60}")
    print(f"Testing with: {test_company}")
    print('=' * 60)
    
    # Get earliest date
    earliest_date = get_earliest_news_date(test_company)
    print(f"✓ Earliest news date: {earliest_date}")
    
    # Get ticker
    ticker = get_stock_ticker(test_company)
    print(f"✓ Stock ticker: {ticker}")
    
    # Fetch stock data
    print("\nFetching stock data...")
    stock_data = fetch_stock_data(test_company)
    
    if stock_data is not None and not stock_data.empty:
        print(f"✓ Stock data retrieved: {len(stock_data)} records")
        print(f"  Date range: {stock_data['Date'].min()} to {stock_data['Date'].max()}")
        print(f"  Columns: {list(stock_data.columns)}")
        print("\nFirst few rows:")
        print(stock_data.head(3))
    else:
        print("✗ No stock data retrieved")
        print("  Note: This could be because:")
        print("  - The ticker symbol might not be correct for this company")
        print("  - The API might be rate-limited")
        print("  - The ticker might not have data for the given date range")

print(f"\n{'=' * 60}")
print("Test completed!")
print('=' * 60)
