
tokenizer = None
model = None
import torch
from pathlib import Path
import kagglehub
import numpy
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from tqdm.notebook import tqdm
from pprint import pprint

# HUGGUING FACE MODEL:
from transformers import AutoTokenizer
from transformers import AutoModelForSequenceClassification
from scipy.special import softmax

import sqlite3

DB_PATH = Path(__file__).parent / "news_database.db"

# nltk.download('averaged_perceptron_tagger_eng')

MODEL = "cardiffnlp/twitter-roberta-base-sentiment"
tokenizer = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForSequenceClassification.from_pretrained(MODEL)


# vader_s = {}
# res = {}
# for i, row in tqdm(db.iterrows(), total =len(db)):
#     keys = db['title'][i]
#     values = sia.polarity_scores(keys)
#     vader_s_rename = {}

#     for key, value in values.items():
#         vader_s_rename[f"vader_{key}"] = value

#     roberta_score = polarity_scores_roberta(keys)
#     both = {**vader_s_rename, **roberta_score}
#     res[i] = both





def polarity_scores_roberta(example):
    if tokenizer is None or model is None:
        raise RuntimeError("Model is not initialized. Check the import/model setup errors above.")

    encoded_text = tokenizer(example, return_tensors='pt')
    output = model(**encoded_text)
    scores = output[0][0].detach().numpy()
    scores = softmax(scores)
    scores_dict = {
        'roberta_neg': float(scores[0]),
        'roberta_neut': float(scores[1]),
        'roberta_pos': float(scores[2])
    }
    return scores_dict


def get_company_time_series(company, db_path=None, resample='D'):
    """Return a resampled DataFrame of mean sentiment scores for `company`.

    - `resample`: pandas resample frequency string, e.g. 'D' (daily), 'W' (weekly), 'M' (monthly).
    """
    if db_path is None:
        db_path = DB_PATH

    conn = sqlite3.connect(str(db_path))
    try:
        df = pd.read_sql_query(
            "SELECT published_date, score, roberta_neg, roberta_neut, roberta_pos FROM articles WHERE company = ? ORDER BY published_date",
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
    ts = df.resample(resample).mean()
    return ts


def plot_company_sentiment(company, db_path=None, resample='D', save_path=None, show=True):
    """Plot sentiment time series for `company`. Returns the resampled DataFrame."""
    ts = get_company_time_series(company, db_path, resample)
    if ts.empty:
        print(f"No data found for {company}")
        return ts

    plt.figure(figsize=(12, 6))
    # plot compound score and the three roberta components
    if 'score' in ts.columns:
        sns.lineplot(data=ts['score'], label='Compound score')
    sns.lineplot(data=ts[['roberta_pos', 'roberta_neut', 'roberta_neg']])

    plt.title(f"Sentiment time series for {company}")
    plt.xlabel("Date")
    plt.ylabel("Score")
    plt.legend()
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path)
        print("Saved sentiment plot to", save_path)

    if show:
        plt.show()

    plt.close()
    return ts



