-- CREATE CLEAN_REVIEWS TABLE
-- This table stores the first cleaned version of raw app reviews.
-- Each row matches one row from raw_reviews by review_id.

CREATE TABLE IF NOT EXISTS clean_reviews (
    review_id TEXT PRIMARY KEY REFERENCES raw_reviews(review_id),
    app_id TEXT NOT NULL REFERENCES apps(app_id),
    app_name TEXT NOT NULL,
    cleaned_review_text TEXT NOT NULL DEFAULT '',
    review_text_length INTEGER NOT NULL DEFAULT 0,
    word_count INTEGER NOT NULL DEFAULT 0,
    is_empty_text BOOLEAN NOT NULL DEFAULT FALSE,
    cleaned_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
