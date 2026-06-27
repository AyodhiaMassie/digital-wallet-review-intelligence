from pathlib import Path
import sys
from typing import Any

import pandas as pd
import yaml

from data_ingestion.sources.google_play import GooglePlayReviewSource
from src.database.ingestion_runs import create_ingestion_run, finish_ingestion_run
from src.database.raw_reviews import insert_raw_reviews
from src.validation.summarize_review_missing_fields import summarize_review_missing_fields
from src.validation.deduplicate_reviews import deduplicate_reviews

PROJECT_ROOT = Path(__file__).resolve().parents[1] # root folder of project
APP_CONFIG_PATH = PROJECT_ROOT / "config" / "apps.yaml" # path to config file

REVIEW_COUNT_PER_APP = 10 # default number of revews fetched per app


def load_app_configs(config_path: Path = APP_CONFIG_PATH) -> list[dict[str, Any]]:
    """
    Load app settings from config/apps.yaml.
    This gets a list of apps with enabled: true
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
    Helper function to fetch a small sample of recent Google Play reviews for one app.
    We return a pandas dataframe where each row represents one review for the app.
    """

    # get the values from the app dictionary
    country = app_config.get("country", "my")
    language = app_config.get("language", "en")

    # initialize google play as a review source
    review_source = GooglePlayReviewSource()
    
    # fetch reviews for the app from google play
    raw_reviews_df = review_source.fetch_reviews(
        app_config=app_config,
        review_count=review_count,
    )

    # list to store app reviews (for one app)
    records = []

    # loop through each review dictionary
    # convert scraper's dict key names into more appropriate names   
    for _, review in raw_reviews_df.iterrows():
        records.append(
            {
                "review_id": review.get("review_id"),
                "app_id": review.get("app_id"),
                "app_name": review.get("app_name"),
                "review_text": review.get("review_text"),
                "rating": review.get("rating"),
                "review_date": review.get("review_date"),
                "scraped_at": review.get("scraped_at"),
                "app_version": review.get("app_version"),
                "thumbs_up_count": review.get("thumbs_up_count"),
                "developer_reply": review.get("developer_reply"),
                "language": language,
                "country": country,
                "source": review.get("source"),
                "app_type": app_config.get("app_type"),
                "wallet_relevance_note": app_config.get("wallet_relevance_note"),
            }
        )

    # convert list of review dictionaries into pandas table 
    return pd.DataFrame(records)  

def fetch_reviews_for_enabled_apps(review_count_per_app: int = REVIEW_COUNT_PER_APP) -> pd.DataFrame:
    """
    Main function which fetches recent reviews for every enabled app in config/apps.yaml.
    """

    # load app configs
    app_configs = load_app_configs() 

    # list to store dataframes of app reviews
    all_review_dataframes = [] 

    # loop through each enabled app
    for app_config in app_configs:
        app_id = app_config["app_id"]
        app_name = app_config["app_name"]
        source = app_config.get("source", "google_play")

        print(f"Fetching {review_count_per_app} reviews for {app_name}...")

        # log new ingestion run
        ingestion_run_id = create_ingestion_run(
            app_id=app_id,
            reviews_requested=review_count_per_app,
            source=source,
        )
        print(f"Started ingestion run {ingestion_run_id} for {app_name}.")

        # create empty dataframe
        app_reviews_df = pd.DataFrame()

        try:
            # fetch reviews for app
            app_reviews_df = fetch_reviews_for_app(
                app_config=app_config, # pass configs for that app
                review_count=review_count_per_app, # pass review count
            )

            reviews_collected = len(app_reviews_df)

            # insert fetched reviews into PostgreSQL
            new_reviews_inserted, db_duplicates_skipped = insert_raw_reviews(
                reviews_df=app_reviews_df,
                ingestion_run_id=ingestion_run_id,
            )

            # end ingestion run
            finish_ingestion_run(
                run_id=ingestion_run_id,
                reviews_collected=reviews_collected,
                new_reviews_inserted=new_reviews_inserted,
                duplicates_skipped=db_duplicates_skipped,
                status="success",
            )

            # print summary
            print(f"Collected {reviews_collected} reviews for {app_name}.")
            print(f"Inserted {new_reviews_inserted} new reviews into PostgreSQL.")
            print(f"Skipped {db_duplicates_skipped} duplicate reviews in PostgreSQL.")
            print(f"Finished ingestion run {ingestion_run_id} with status: success.")

        # if fetch reviews failed handle it
        except Exception as error:
            error_message = str(error)

            # finish the ingestion run with status = failed
            finish_ingestion_run(
                run_id=ingestion_run_id,
                reviews_collected=len(app_reviews_df),
                new_reviews_inserted=0,
                duplicates_skipped=0,
                status="failed",
                errors=error_message,
            )

            print(f"Failed ingestion run {ingestion_run_id} for {app_name}.")
            print(f"Error: {error_message}")

            continue

        # add dataframe of app reviews into all_review_dataframes list
        all_review_dataframes.append(app_reviews_df)

    # handle case if there were no app review dataframes
    if not all_review_dataframes:
        return pd.DataFrame()

    # combine each individual app review dataframe into one big dataframe
    all_app_reviews_df = pd.concat(all_review_dataframes, ignore_index=True)
    
    # create a set of app IDs that we expect to see in the fetched reviews
    expected_app_ids = {app_config["app_id"] for app_config in app_configs}

    # get summarized information on missing fields in the all app reviews dataframe
    missing_field_summary = summarize_review_missing_fields(
    review_df=all_app_reviews_df,
    expected_app_ids=expected_app_ids,
    )

    # print out the summarized information
    print("\nSummary of missing fields in all app review dataframe:")
    for field_name, value in missing_field_summary.items():
        print(f"{field_name}: {value}")
    
    # deduplicate all reviews dataframe
    deduplicated_reviews_df, duplicates_skipped = deduplicate_reviews(
        review_df=all_app_reviews_df
    )

    # print out number of duplicate reviews skipped
    print(f"\nDuplicates skipped: {duplicates_skipped}")

    return deduplicated_reviews_df

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
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    df = fetch_reviews_for_enabled_apps() 

    print()
    print(f"Collected {len(df)} reviews in total.")
    print()

    review_counts = df.groupby(["app_id", "app_name"]).size().reset_index(name="review_count")

    print("Review counts by app:")
    print(review_counts.to_string(index=False))
    print()

    print_review_cards(df, max_reviews=10)
