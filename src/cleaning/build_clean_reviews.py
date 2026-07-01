from sqlalchemy import text

from src.cleaning.text_cleaning import (
    clean_review_text,
    count_words,
    is_empty_text,
)
from src.database.connection import get_database_engine

def fetch_raw_reviews(connection) -> list[dict]:
    """Read the review_id, app_id, app_name, and review_text from the raw_reviews table"""
    
    # create sql query
    # reads review_id, app_id, app_name, and review_text from raw_reviews table
    sql = text(
        """
        SELECT
            review_id,
            app_id,
            app_name,
            review_text
        FROM raw_reviews
        ORDER BY inserted_at, review_id;
        """
    )

    # send the sql query to postgresql
    result = connection.execute(sql)

    # returns list of dictionaries where 
    # each dictionary contains the selected review fields of each review 
    return [dict(row) for row in result.mappings()]


def prepare_clean_review(raw_review: dict) -> dict:
    """Clean one raw review and prepare it for database insertion."""
    cleaned_review_text = clean_review_text(raw_review["review_text"])

    return {
        "review_id": raw_review["review_id"],
        "app_id": raw_review["app_id"],
        "app_name": raw_review["app_name"],
        "cleaned_review_text": cleaned_review_text,
        "review_text_length": len(cleaned_review_text),
        "word_count": count_words(cleaned_review_text),
        "is_empty_text": is_empty_text(cleaned_review_text),
    }


def upsert_clean_reviews(connection, clean_reviews: list[dict]) -> int:
    """Insert clean reviews, or update them if they already exist."""
    
    # if there are no clean reviews to return, stop and return 0
    if not clean_reviews:
        return 0

    # create sql query
    # inserts cleaned review into clean_reviews sql table
    sql = text(
        """
        INSERT INTO clean_reviews (
            review_id,
            app_id,
            app_name,
            cleaned_review_text,
            review_text_length,
            word_count,
            is_empty_text
        )
        VALUES (
            :review_id,
            :app_id,
            :app_name,
            :cleaned_review_text,
            :review_text_length,
            :word_count,
            :is_empty_text
        )
        ON CONFLICT (review_id) DO UPDATE
        SET
            app_id = EXCLUDED.app_id,
            app_name = EXCLUDED.app_name,
            cleaned_review_text = EXCLUDED.cleaned_review_text,
            review_text_length = EXCLUDED.review_text_length,
            word_count = EXCLUDED.word_count,
            is_empty_text = EXCLUDED.is_empty_text,
            cleaned_at = CURRENT_TIMESTAMP;
        """
    )

    # set a counter to track each review that gets inserted
    updated_count = 0

    # loop through each clean review
    # upsert that clean review
    # update the updated_count counter
    for clean_review in clean_reviews:
        result = connection.execute(sql, clean_review)
        updated_count += result.rowcount

    # return the count of number of rows updated (inserted/updated)
    return updated_count


def build_clean_reviews() -> None:
    """Build the clean_reviews table from raw_reviews."""
    engine = get_database_engine()

    with engine.begin() as connection:

        # get the raw reviews as list of dictionaries
        raw_reviews = fetch_raw_reviews(connection)
        
        # create list of dictionaries of clean reviews
        clean_reviews = [
            prepare_clean_review(raw_review)
            for raw_review in raw_reviews
        ]

        # inserts or updates the cleaned review into the clean_reviews database
        # returns the count of rows upserted
        inserted_or_updated_count = upsert_clean_reviews(connection, clean_reviews)

    # counts how many cleaned reviews are empty
    empty_text_count = sum(
        1
        for clean_review in clean_reviews
        if clean_review["is_empty_text"]
    )

    print("Clean reviews build complete.")
    print(f"Raw reviews found: {len(raw_reviews)}")
    print(f"Clean reviews inserted or updated: {inserted_or_updated_count}")
    print(f"Empty cleaned texts: {empty_text_count}")


if __name__ == "__main__":
    build_clean_reviews()
