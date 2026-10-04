import requests
from bs4 import BeautifulSoup
import json
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta, timezone
from SentimentAnalysis import polarity_scores_roberta
import time

print("STEP 1: Program started")
NEWS_API_KEY = "f046c6f6fd4449aab320b83d4bf61096"
COMPANY = input("Enter Company: ")

print("STEP 2: Company entered:", COMPANY)
url = "https://newsapi.org/v2/everything"

end_date = datetime(2026, 8, 3, tzinfo=timezone.utc)
start_date = end_date - timedelta(days=45)

params = {
    "q": f"{COMPANY} AND (finance OR financial OR stock OR market OR earnings OR investment)",
    "language": "en",
    "from": start_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
    "to": end_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
    "sortBy": "publishedAt",
    "pageSize": 100,
    "page": 1,
    "apiKey": NEWS_API_KEY,
}

#----------------------------------------------
#       REQUESTING DATA THROUGH API
#----------------------------------------------

all_articles = []
max_pages = 10
print(f"STEP 3: Fetching {COMPANY} articles from {params['from']} to {params['to']}...")
print(f"STEP 3B: Will request pages 1 through {max_pages} sequentially")

for page in range(1, max_pages + 1):
    params["page"] = page
    print(f"STEP 4: Sending request for page {page}...")
    response = requests.get(url, params=params, timeout=20)
    print(f"STEP 4A: API status code on page {page}:", response.status_code)

    if response.status_code == 426:
        print("STEP 5: NewsAPI rejected additional pages for this plan. Continuing with the available 30-day results.")
        break

    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as exc:
        print(f"STEP 5: API request failed: {exc}")
        break

    data = response.json()
    articles = data.get("articles", [])
    print(f"STEP 5: Page {page} returned {len(articles)} articles")

    if not articles:
        print(f"STEP 5A: No more articles returned on page {page}; stopping pagination.")
        break

    all_articles.extend(articles)

    if len(articles) < params["pageSize"]:
        print(f"STEP 5A: Fewer than {params['pageSize']} articles returned on page {page}; stopping pagination.")
        break

    # small pause between requests so the API doesn't block you
    time.sleep(1)

print(f"STEP 5B: Total articles collected for this 30-day window: {len(all_articles)}")

# NewsAPI already filters by language, so no domain restriction is applied.
# This fetches global English-language articles worldwide.
print("STEP 5C: Using global English-language NewsAPI results")

# print(json.dumps(data, indent=2))

#----------------------------------------------
#          CONNECTING TO SQLITE3
#----------------------------------------------

DB_PATH = Path(__file__).parent / "news_database.db"
print("STEP 6: Connecting to SQLite3 database at", DB_PATH)
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# create table if not exists
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company TEXT,
        title TEXT,
        published_date TEXT,
        description TEXT,
        sentiment TEXT,
        score REAL,
        roberta_neg REAL,
        roberta_neut REAL,
        roberta_pos REAL,
        url TEXT,
        source TEXT,
        UNIQUE(company, title, published_date)
    )
    """
)
conn.commit()

print("STEP 7: SQLite connected and table ensured")

#----------------------------------------------
#        INSERTING DATA INTO TABLES
#----------------------------------------------
articles = all_articles

for d in articles:
    company = COMPANY
    title = d.get("title") or "No title"
    article_url = d.get("url") or ""

    published_at = d.get("publishedAt")
    if published_at:
        try:
            published_date = datetime.fromisoformat(published_at.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            published_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    else:
        published_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    description = d.get("description") or ""
    article_url = d.get("url") or ""
    source_data = d.get("source") or {}
    source = source_data.get("name") if isinstance(source_data, dict) else "Unknown"

    #----------------------------------------------
    #          SENTIMENT ANALYSIS
    #----------------------------------------------
    scores = polarity_scores_roberta(title)
    roberta_neg = scores.get("roberta_neg")
    roberta_neut = scores.get("roberta_neut")
    roberta_pos = scores.get("roberta_pos")
    compound_score = roberta_pos - roberta_neg

    if compound_score > 0.05:
        sentiment = "Positive"
    elif compound_score < -0.05:
        sentiment = "Negative"
    else:
        sentiment = "Neutral"

    sql = """
    INSERT OR IGNORE INTO articles
    (company, title, published_date, description, sentiment, score, roberta_neg, roberta_neut, roberta_pos, url, source)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    values = (
        company,
        title,
        published_date,
        description,
        sentiment,
        compound_score,
        roberta_neg,
        roberta_neut,
        roberta_pos,
        article_url,
        source,
    )

    cursor.execute(sql, values)

print("STEP 8: All articles processed, committing to DB")
conn.commit()

try:
    from plot_sentiment import build_daily_sentiment_stock_table
    build_daily_sentiment_stock_table(DB_PATH, company=COMPANY)
    print(f"STEP 9: Daily sentiment and close-price aggregate refreshed for {COMPANY}")
except Exception as exc:
    print(f"STEP 9: Could not refresh daily aggregate table: {exc}")

print("Articles stored successfully!")

cursor.close()
conn.close()