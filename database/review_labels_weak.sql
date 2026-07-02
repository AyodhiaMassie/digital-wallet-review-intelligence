-- CREATE REVIEW_LABELS_WEAK TABLE
-- This table stores rule-based weak labels for cleaned reviews.
-- Each row matches one row from clean_reviews by review_id.
-- For the MVP, each review gets one weak label row.

CREATE TABLE IF NOT EXISTS review_labels_weak (
    review_id TEXT PRIMARY KEY REFERENCES clean_reviews(review_id),
    app_id TEXT NOT NULL REFERENCES apps(app_id),
    scope_label TEXT NOT NULL,
    issue_label TEXT NOT NULL,
    matched_scope_terms JSONB NOT NULL DEFAULT '[]'::jsonb,
    matched_issue_terms JSONB NOT NULL DEFAULT '[]'::jsonb,
    rule_confidence NUMERIC NOT NULL CHECK (rule_confidence BETWEEN 0 AND 1),
    label_version TEXT NOT NULL DEFAULT 'v1',
    labelled_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
