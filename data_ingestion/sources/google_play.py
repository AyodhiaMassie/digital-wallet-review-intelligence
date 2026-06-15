from typing import Any
from datetime import datetime, timezone

import pandas as pd
from google_play_scraper import Sort, reviews

from data_ingestion.sources.base import ReviewSource # import review source base class

class GooglePlayReviewSource(ReviewSource):
    """
    Google play store review source implementation.
    """

    def fetch_reviews(
        self,
        app_config: dict[str, Any],
        review_count: int,
    ) -> pd.DataFrame:
        """
        Fetch reviews for one Google Play app.
        """

        app_id = app_config["app_id"]
        app_name = app_config["app_name"]

        # call reviews() function which fetches list of app review dictionaries (each dictionary = one review)
        review_list, continuation_token = reviews(
            app_id,
            lang="en",
            country="my",
            sort=Sort.NEWEST,
            count=review_count,
        )
        _ = continuation_token

        # standard columns
        standard_columns = [
            "review_id",
            "app_id",
            "app_name",
            "review_text",
            "rating",
            "review_date",
            "scraped_at",
            "app_version",
            "thumbs_up_count",
            "developer_reply",
            "language",
            "source"
        ] 

        # convert the list of app review dictionaries into a pandas dataframe
        review_df = pd.DataFrame(review_list)

        print("RAW GOOGLE PLAY DATAFRAME COLUMNS:")
        print(review_df.columns)

        print("RAW GOOGLE PLAY DATAFRAME PREVIEW:")
        print(review_df.head())

        # standardize column names
        review_df = review_df.rename(
            columns={

            "reviewId": "review_id",
            "content": "review_text",
            "score": "rating",
            "at": "review_date",
            "reviewCreatedVersion": "app_version",
            "thumbsUpCount": "thumbs_up_count",
            "replyContent": "developer_reply", 

            }
        )

        # handle case that scraper returns no reviews
        if review_df.empty:
            return pd.DataFrame(columns=standard_columns)

        # add relavent column to the dataframe
        review_df["app_id"] = app_id
        review_df["app_name"] = app_name
        review_df["scraped_at"] =  datetime.now(timezone.utc)
        review_df["source"] = "google_play"
        review_df["language"] = "en"

        # verify that all standard columns exist in the review dataframe
        for column in standard_columns:
            if column not in review_df.columns:
                review_df[column] = None

        # retain only the standard columns
        review_df = review_df[standard_columns]

        # return the dataframe
        return review_df
