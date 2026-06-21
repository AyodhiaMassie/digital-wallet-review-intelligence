import pandas as pd
from sqlalchemy import text

from src.database.connection import get_database_engine

# list of columns from raw_reviews dataframe created from the scraper
RAW_REVIEW_COLUMNS = [
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
    "source",
]

# handle missing values in the dataframe
def clean_missing_value(value):
    if pd.isna(value):
        return None
    return value

# 
def prepare_review_row(review_row: dict, ingestion_run_id: int) -> dict:
    
    # dictionary that stores a raw review, ready to be inserted into the database
    prepared_row = {}

    # insert into prepared_row dictionary the expected columns from RAW_REVIEW_COLUMNS as a key
    # and the corresponding value from the actual raw review as the value (cleaned)
    for column in RAW_REVIEW_COLUMNS:
        prepared_row[column] = clean_missing_value(review_row.get(column))

    # add the ingestion_run_id into the prepared_row dict
    prepared_row["ingestion_run_id"] = ingestion_run_id

    # return the prepared_row dictionary
    return prepared_row


def insert_raw_reviews(reviews_df: pd.DataFrame, ingestion_run_id: int) -> tuple[int, int]:
    
    # handle case that scraper returned no reviews, return 0 inserted and duplicates skipped
    if reviews_df.empty:
        return 0, 0

    # get database engine
    engine = get_database_engine()

    # sql query that inserts a row into raw_reviews database
    sql = text(
        """
        INSERT INTO raw_reviews (
            review_id,
            app_id,
            app_name,
            review_text,
            rating,
            review_date,
            scraped_at,
            app_version,
            thumbs_up_count,
            developer_reply,
            language,
            source,
            ingestion_run_id
        )
        VALUES (
            :review_id,
            :app_id,
            :app_name,
            :review_text,
            :rating,
            :review_date,
            :scraped_at,
            :app_version,
            :thumbs_up_count,
            :developer_reply,
            :language,
            :source,
            :ingestion_run_id
        )
        ON CONFLICT (review_id) DO NOTHING;
        """
    )

    # convert raw_reviews dataframe into a list of dictionaries (each row corresponds to one dict)
    review_rows = reviews_df.to_dict(orient="records")
    
    # prepare all raw reviews to be inserted into the raw_reviews database
    prepared_rows = [
        prepare_review_row(review_row, ingestion_run_id)
        for review_row in review_rows
    ]

    # counter to track how many review rows were inserted into raw_reviews database
    inserted_count = 0

    # opens database transaction
    with engine.begin() as connection:
        
        # for each prepared row, insert it into the raw_reviews database
        for prepared_row in prepared_rows:

            # sql query adds a row and names the placeholders
            # placeholder values are then binded by the prepared_row dictionary 
            result = connection.execute(sql, prepared_row)
            inserted_count += result.rowcount

    # get the number of duplicate reviews skipped
    duplicates_skipped = len(prepared_rows) - inserted_count

    # return the number of reviews inserted and number of duplicate reviews skipped
    return inserted_count, duplicates_skipped