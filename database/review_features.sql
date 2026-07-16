-- CREATE REVIEW_FEATURES TABLE
-- This table stores model input features created from clean_reviews and raw review metadata.
-- It should not contain target labels, manual labels, weak labels, model predictions, or downstream outputs.
-- Text-derived features and metadata features are allowed based on config/allowed_features.yaml.
-- Forbidden values are documented in config/forbidden_features.yaml.
-- TF-IDF vectors are not stored here yet because they are usually created during model training.

CREATE TABLE IF NOT EXISTS review_features (
    review_id TEXT PRIMARY KEY REFERENCES clean_reviews(review_id),
    app_id TEXT NOT NULL REFERENCES apps(app_id),
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    app_version TEXT,
    review_date TIMESTAMP,
    day_of_week INTEGER CHECK (day_of_week BETWEEN 0 AND 6),
    review_text_length INTEGER CHECK (review_text_length >= 0),
    word_count INTEGER CHECK (word_count >= 0),

    has_money_loss_terms BOOLEAN NOT NULL DEFAULT FALSE,
    has_payment_failure_terms BOOLEAN NOT NULL DEFAULT FALSE,
    has_refund_terms BOOLEAN NOT NULL DEFAULT FALSE,
    has_fraud_scam_terms BOOLEAN NOT NULL DEFAULT FALSE,
    has_login_otp_terms BOOLEAN NOT NULL DEFAULT FALSE,
    has_kyc_terms BOOLEAN NOT NULL DEFAULT FALSE,
    has_support_terms BOOLEAN NOT NULL DEFAULT FALSE,
    has_crash_bug_terms BOOLEAN NOT NULL DEFAULT FALSE,
    has_promo_reward_terms BOOLEAN NOT NULL DEFAULT FALSE,

    feature_set_version TEXT NOT NULL DEFAULT 'features_v1',
    features_generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
