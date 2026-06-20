-- CREATE APPS TABLE
CREATE TABLE IF NOT EXISTS apps (

    app_id TEXT PRIMARY KEY,
    app_name TEXT NOT NULL,
    country TEXT NOT NULL DEFAULT 'my',
    source TEXT NOT NULL DEFAULT 'google_play',
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- CREATE INGESTION_RUNS TABLE

CREATE TABLE IF NOT EXISTS ingestion_runs (
    run_id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    app_id TEXT NOT NULL REFERENCES apps(app_id),
    started_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP,
    reviews_requested INTEGER NOT NULL,
    reviews_collected INTEGER NOT NULL DEFAULT 0,
    new_reviews_inserted INTEGER NOT NULL DEFAULT 0,
    duplicates_skipped INTEGER NOT NULL DEFAULT 0,
    errors TEXT,
    status TEXT NOT NULL
);

-- CREATE RAW_REVIEWS TABLE

CREATE TABLE IF NOT EXISTS raw_reviews (
    review_id TEXT PRIMARY KEY,
    app_id TEXT NOT NULL REFERENCES apps(app_id),
    app_name TEXT NOT NULL,
    review_text TEXT,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    review_date TIMESTAMP NOT NULL,
    scraped_at TIMESTAMP NOT NULL,
    app_version TEXT,
    thumbs_up_count INTEGER,
    developer_reply TEXT,
    language TEXT,
    source TEXT NOT NULL,
    ingestion_run_id BIGINT REFERENCES ingestion_runs(run_id),
    inserted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

SELECT * FROM apps;