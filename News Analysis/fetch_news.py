import requests
from bs4 import BeautifulSoup
import json
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import sqlite3
from pathlib import Path
from datetime import datetime
from SentimentAnalysis import polarity_scores_roberta
import time

print("STEP 1: Program started")
NEWS_API_KEY = "f046c6f6fd4449aab320b83d4bf61096"
COMPANY = "Airtel"

print("STEP 2: Company entered:", COMPANY)
url = "https://newsapi.org/v2/everything"

params = {
    "q": COMPANY,
    "language": "en",
    "sortBy": "publishedAt",
    "pageSize": 50,
    "apiKey": NEWS_API_KEY,
}

#----------------------------------------------
#       REQUESTING DATA THROUGH API
#----------------------------------------------

print(f"STEP 3: Sending API request...")
response = requests.get(url, params=params, timeout=20)
print("STEP 4: API status code:", response.status_code)

response.raise_for_status()
data = response.json()
print("STEP 5: API response received")

# NewsAPI already filters by language, so no domain restriction is applied.
# This fetches global English-language articles worldwide.
print("STEP 5B: Using global English-language NewsAPI results")



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
articles = data.get("articles", [])

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
print("Articles stored successfully!")

cursor.close()
conn.close()
