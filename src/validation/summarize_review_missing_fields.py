from typing import Any

import pandas as pd

def summarize_review_missing_fields(
    review_df: pd.DataFrame, # dataframe which stores reviews
    expected_app_ids: set[str], # set of expected app id's
) -> dict[str, Any]: # return type -> dict containing summary statistics on reviews
    
    # get total review count (number of rows in the review dataframe)
    total_reviews = len(review_df)
    """
    function to validate all fields in the reviews dataframe do not contain unexpected values
    
    """

    # handle case: empty review dataframe
    if total_reviews == 0:
        return {
            "total_reviews": 0,
            "missing_review_id_count": 0,
            "duplicate_review_id_count": 0,
            "missing_review_text_count": 0,
            "invalid_rating_count": 0,
            "invalid_review_date_count": 0,
            "unexpected_app_id_count": 0,
            "missing_app_version_count": 0,
            "missing_app_version_rate": 0.0,
        }

    # convert review dataframe column names into variables
    review_ids = review_df["review_id"]
    review_text = review_df["review_text"]
    ratings = pd.to_numeric(review_df["rating"], errors="coerce")
    review_dates = pd.to_datetime(review_df["review_date"], errors="coerce")
    app_ids = review_df["app_id"]
    app_versions = review_df["app_version"]

    # get total count of review rows with a missing review id
    missing_review_id_count = review_ids.isna().sum()

    # get total count of review rows that has the same (duplicate) review id
    duplicate_review_id_count = review_ids.duplicated().sum()

    # get total count of review rows that has missing review text, checks whether:
    # 1. review_text column is blank
    # 2. review_text column is a string with only whitespaces or is blank
    missing_review_text_count = (
        review_text.isna() | review_text.astype(str).str.strip().eq("")
    ).sum()

    # get total count of review rows that has an invalid rating, checks whether:
    # 1. rating column is blank
    # 2. rating column is not blank but not within the expected rating range of 1-5
    invalid_rating_count = (
        ratings.isna() | ~ratings.between(1, 5)
    ).sum()

    # get total count of review rows that has an invalid date
    invalid_review_date_count = review_dates.isna().sum()

    # get total count of review rows that has an app_id that was not meant to have its reviews scraped through
    unexpected_app_id_count = (
        app_ids.isna() | ~app_ids.isin(expected_app_ids)
    ).sum()

    # get total count of review rows that has a missing app version
    missing_app_version_count = (
        app_versions.isna() | app_versions.astype(str).str.strip().eq("")
    ).sum()

    # get the proportion of review rows with a missing app version
    missing_app_version_rate = missing_app_version_count / total_reviews

    # return summary statistics of missing fields in the review dataframe
    return {
        "total_reviews": total_reviews,
        "missing_review_id_count": int(missing_review_id_count),
        "duplicate_review_id_count": int(duplicate_review_id_count),
        "missing_review_text_count": int(missing_review_text_count),
        "invalid_rating_count": int(invalid_rating_count),
        "invalid_review_date_count": int(invalid_review_date_count),
        "unexpected_app_id_count": int(unexpected_app_id_count),
        "missing_app_version_count": int(missing_app_version_count),
        "missing_app_version_rate": round(missing_app_version_rate, 4),
    }