-- CREATE REVIEW_LABELS_MANUAL TABLE
-- This table stores trusted human-labelled labels for cleaned reviews.
-- These manual labels are the trusted will help in evaluating our model
-- This table is intentionally smaller than review_labels_weak, so not every clean review needs a manual label.
-- Weak labels are automatic guesses; manual labels are the trusted labels created or reviewed by a person.

CREATE TABLE IF NOT EXISTS review_labels_manual (
    review_id TEXT PRIMARY KEY REFERENCES clean_reviews(redview_id),
    scope_label TEXT NOT NULL CHECK (scope_label IN (
        'wallet_related',
        'non_wallet_related',
        'unclear'
    )),
    primary_issue_label TEXT NOT NULL,
    priority_label TEXT NOT NULL CHECK (priority_label IN (
        'high',
        'medium',
        'low',
        'unclear'
    )),
    labelled_by TEXT,
    labelled_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    label_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
