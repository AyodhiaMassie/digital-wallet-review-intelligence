from datetime import date, datetime

from sqlalchemy import text

from src.cleaning.text_cleaning import count_words
from src.database.connection import get_database_engine

FEATURE_SET_VERSION = "features_v1"

INDICATOR_KEYWORDS = {
    "has_money_loss_terms": [
        "deducted",
        "money deducted",
        "charged",
        "lost money",
        "balance gone",
    ],
    "has_payment_failure_terms": [
        "failed",
        "transaction failed",
        "payment failed",
        "transfer failed",
        "unsuccessful",
    ],
    "has_refund_terms": [
        "refund",
        "dispute",
        "reverse",
        "reversal",
    ],
    "has_fraud_scam_terms": [
        "scam",
        "fraud",
        "unauthorized",
        "unauthorised",
        "hacked",
    ],
    "has_login_otp_terms": [
        "login",
        "log in",
        "otp",
        "password",
        "verification code",
    ],
    "has_kyc_terms": [
        "kyc",
        "verify",
        "verification",
        "identity",
        "ic",
        "document",
    ],
    "has_support_terms": [
        "support",
        "customer service",
        "no reply",
        "help",
        "agent",
    ],
    "has_crash_bug_terms": [
        "crash",
        "bug",
        "error",
        "lag",
        "freeze",
        "stuck",
    ],
    "has_promo_reward_terms": [
        "cashback",
        "reward",
        "voucher",
        "promo",
        "points",
    ],
}


def fetch_eligible_clean_reviews(connection) -> list[dict]:
    """Read clean reviews and raw review metadata needed for feature building."""

    sql = text(
        """
        SELECT
            clean_reviews.review_id,
            clean_reviews.app_id,
            clean_reviews.cleaned_review_text,
            raw_reviews.rating,
            raw_reviews.app_version,
            raw_reviews.review_date
        FROM clean_reviews
        INNER JOIN raw_reviews
            ON clean_reviews.review_id = raw_reviews.review_id
        WHERE clean_reviews.cleaned_review_text IS NOT NULL
            AND TRIM(clean_reviews.cleaned_review_text) <> ''
        ORDER BY clean_reviews.review_id;
        """
    )

    result = connection.execute(sql)
    return [dict(row) for row in result.mappings()]


def has_any_keyword(review_text: str, keywords: list[str]) -> bool:
    """Check whether any keyword or phrase appears in the review text."""

    review_text_lower = review_text.lower()

    for keyword in keywords:
        if keyword.lower() in review_text_lower:
            return True

    return False


def get_day_of_week(review_date: date | datetime | None) -> int | None:
    """Return day of week as 0 to 6, where Monday is 0 and Sunday is 6."""

    if review_date is None:
        return None

    return review_date.weekday()


def prepare_review_feature(clean_review: dict) -> dict:
    """Calculate model input features for one cleaned review."""

    cleaned_review_text = clean_review["cleaned_review_text"]
    review_feature = {
        "review_id": clean_review["review_id"],
        "app_id": clean_review["app_id"],
        "rating": clean_review["rating"],
        "app_version": clean_review["app_version"],
        "review_date": clean_review["review_date"],
        "day_of_week": get_day_of_week(clean_review["review_date"]),
        "review_text_length": len(cleaned_review_text),
        "word_count": count_words(cleaned_review_text),
        "feature_set_version": FEATURE_SET_VERSION,
    }

    for indicator_name, keywords in INDICATOR_KEYWORDS.items():
        review_feature[indicator_name] = has_any_keyword(
            cleaned_review_text,
            keywords,
        )

    return review_feature


def build_review_feature_rows(clean_reviews: list[dict]) -> list[dict]:
    """Build feature rows in memory without using labels or predictions."""

    return [
        prepare_review_feature(clean_review)
        for clean_review in clean_reviews
    ]


def upsert_review_features(connection, review_features: list[dict]) -> int:
    """Insert review features, or update them if they already exist."""

    if not review_features:
        return 0

    sql = text(
        """
        INSERT INTO review_features (
            review_id,
            app_id,
            rating,
            app_version,
            review_date,
            day_of_week,
            review_text_length,
            word_count,
            has_money_loss_terms,
            has_payment_failure_terms,
            has_refund_terms,
            has_fraud_scam_terms,
            has_login_otp_terms,
            has_kyc_terms,
            has_support_terms,
            has_crash_bug_terms,
            has_promo_reward_terms,
            feature_set_version
        )
        VALUES (
            :review_id,
            :app_id,
            :rating,
            :app_version,
            :review_date,
            :day_of_week,
            :review_text_length,
            :word_count,
            :has_money_loss_terms,
            :has_payment_failure_terms,
            :has_refund_terms,
            :has_fraud_scam_terms,
            :has_login_otp_terms,
            :has_kyc_terms,
            :has_support_terms,
            :has_crash_bug_terms,
            :has_promo_reward_terms,
            :feature_set_version
        )
        ON CONFLICT (review_id) DO UPDATE
        SET
            app_id = EXCLUDED.app_id,
            rating = EXCLUDED.rating,
            app_version = EXCLUDED.app_version,
            review_date = EXCLUDED.review_date,
            day_of_week = EXCLUDED.day_of_week,
            review_text_length = EXCLUDED.review_text_length,
            word_count = EXCLUDED.word_count,
            has_money_loss_terms = EXCLUDED.has_money_loss_terms,
            has_payment_failure_terms = EXCLUDED.has_payment_failure_terms,
            has_refund_terms = EXCLUDED.has_refund_terms,
            has_fraud_scam_terms = EXCLUDED.has_fraud_scam_terms,
            has_login_otp_terms = EXCLUDED.has_login_otp_terms,
            has_kyc_terms = EXCLUDED.has_kyc_terms,
            has_support_terms = EXCLUDED.has_support_terms,
            has_crash_bug_terms = EXCLUDED.has_crash_bug_terms,
            has_promo_reward_terms = EXCLUDED.has_promo_reward_terms,
            feature_set_version = EXCLUDED.feature_set_version,
            features_generated_at = now(),
            updated_at = now();
        """
    )

    inserted_or_updated_count = 0

    for review_feature in review_features:
        result = connection.execute(sql, review_feature)
        inserted_or_updated_count += result.rowcount

    return inserted_or_updated_count


def main() -> None:
    """Build review_features rows from clean_reviews and raw review metadata."""

    engine = get_database_engine()

    with engine.begin() as connection:
        clean_reviews = fetch_eligible_clean_reviews(connection)
        review_features = build_review_feature_rows(clean_reviews)
        inserted_or_updated_count = upsert_review_features(
            connection,
            review_features,
        )

    print("Review features build complete.")
    print(f"Eligible clean reviews found: {len(clean_reviews)}")
    print(f"Feature rows inserted or updated: {inserted_or_updated_count}")
    print(f"Feature set version used: {FEATURE_SET_VERSION}")
    print("Labels and predictions were not used as features.")


if __name__ == "__main__":
    main()
