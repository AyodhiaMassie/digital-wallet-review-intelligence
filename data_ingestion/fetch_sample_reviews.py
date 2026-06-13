from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml
from google_play_scraper import Sort, reviews


PROJECT_ROOT = Path(__file__).resolve().parents[1] # root folder of project
APP_CONFIG_PATH = PROJECT_ROOT / "config" / "apps.yaml" # path to config file

REVIEW_COUNT_PER_APP = 10 # default number of revews fetched per app

def load_app_configs(config_path: Path = APP_CONFIG_PATH) -> list[dict[str, Any]]:
    """
    
    Load app settings from config/apps.yaml.
    Only apps with enabled: true are returned.
    """

    # open and read the yaml file and converts it into python dict
    with open(config_path, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file) 

    # get the list of apps
    apps = config.get("apps", [])

    # list to store apps enabled for scraping
    enabled_apps = []

    # add enabled apps to the list
    for app in apps:
        if app.get("enabled", False):
            enabled_apps.append(app)

    return enabled_apps


def fetch_reviews_for_app(app_config: dict[str, Any], review_count: int) -> pd.DataFrame:
    """
    Fetch a small sample of recent Google Play reviews for one app.
    """

    # get the values from the app dictionary
    app_id = app_config["app_id"]
    app_name = app_config["app_name"]
    country = app_config.get("country", "my")
    language = app_config.get("language", "en")
    source = app_config.get("source", "google_play")

    # reviews function fetches the reviews and returns it as a list of review dictionaries
    raw_reviews, _ = reviews(
        app_id,
        lang=language,
        country=country,
        sort=Sort.NEWEST,
        count=review_count,
    )

    # records date and time that data was scraped
    scraped_at = datetime.now(timezone.utc).isoformat()

    # list to store app reviews (for one app)
    records = []

    # loop through each review dictionary
    # convert scraper's dict key names into more appropriate names   
    for review in raw_reviews:
        records.append(
            {
                "review_id": review.get("reviewId"),
                "app_id": app_id,
                "app_name": app_name,
                "review_text": review.get("content"),
                "rating": review.get("score"),
                "review_date": review.get("at"),
                "scraped_at": scraped_at,
                "app_version": review.get("reviewCreatedVersion"),
                "thumbs_up_count": review.get("thumbsUpCount"),
                "developer_reply": review.get("replyContent"),
                "language": language,
                "country": country,
                "source": source,
                "app_type": app_config.get("app_type"),
                "wallet_relevance_note": app_config.get("wallet_relevance_note"),
            }
        )

    # convert list of review dictionaries into pandas table 
    return pd.DataFrame(records)  

def fetch_reviews_for_enabled_apps(review_count_per_app: int = REVIEW_COUNT_PER_APP) -> pd.DataFrame:
    """
    Fetch recent reviews for every enabled app in config/apps.yaml.
    """

    # load app configs
    app_configs = load_app_configs() 

    # list to store dataframes of app reviews
    all_review_dataframes = [] 

    # loop through each enabled app
    for app_config in app_configs:
        print(f"Fetching {review_count_per_app} reviews for {app_config['app_name']}...")

        # fetch reviews for app
        app_reviews_df = fetch_reviews_for_app(
            app_config=app_config,
            review_count=review_count_per_app,
        )

        # add dataframe of app reviews into all_review_dataframes list
        all_review_dataframes.append(app_reviews_df)

    # handle case if there were no app review dataframes
    if not all_review_dataframes:
        return pd.DataFrame()

    # combine each individual app review dataframe into one big dataframe
    return pd.concat(all_review_dataframes, ignore_index=True)

# 
def print_review_cards(df: pd.DataFrame, max_reviews: int = 10) -> None:
    """
    Print reviews in a readable vertical format for manual inspection.
    """

    for index, row in df.head(max_reviews).iterrows():
        developer_reply = row["developer_reply"]

        if pd.isna(developer_reply):
            developer_reply = "No developer reply"

        app_version = row["app_version"]

        if pd.isna(app_version):
            app_version = "Missing"

        print("=" * 100)
        print(f"Review #{index + 1}")
        print("=" * 100)
        print(f"Review ID:       {row['review_id']}")
        print(f"App:             {row['app_name']} ({row['app_id']})")
        print(f"App type:        {row['app_type']}")
        print(f"Rating:          {row['rating']}")
        print(f"Review date:     {row['review_date']}")
        print(f"Scraped at:      {row['scraped_at']}")
        print(f"App version:     {app_version}")
        print(f"Thumbs up:       {row['thumbs_up_count']}")
        print(f"Language:        {row['language']}")
        print(f"Country:         {row['country']}")
        print(f"Source:          {row['source']}")
        print()
        print("Review text:")
        print(row["review_text"])
        print()
        print("Developer reply:")
        print(developer_reply)
        print()


if __name__ == "__main__":
    df = fetch_reviews_for_enabled_apps()

    print()
    print(f"Collected {len(df)} reviews in total.")
    print()

    review_counts = df.groupby(["app_id", "app_name"]).size().reset_index(name="review_count")

    print("Review counts by app:")
    print(review_counts.to_string(index=False))
    print()

    print_review_cards(df, max_reviews=10)