from sqlalchemy import text

from src.database.connection import get_database_engine


BOOLEAN_INDICATOR_COLUMNS = [
    "has_money_loss_terms",
    "has_payment_failure_terms",
    "has_refund_terms",
    "has_fraud_scam_terms",
    "has_login_otp_terms",
    "has_kyc_terms",
    "has_support_terms",
    "has_crash_bug_terms",
    "has_promo_reward_terms",
]

FORBIDDEN_FEATURE_COLUMNS = [
    "scope_label",
    "primary_issue_label",
    "priority_label",
    "weak_scope_label",
    "weak_primary_issue_label",
    "manual_scope_label",
    "manual_primary_issue_label",
    "manual_priority_label",
    "predicted_issue",
    "issue_confidence",
    "priority_score",
    "priority_band",
    "recommended_team",
    "reason_codes",
    "model_version",
]


def print_section(title: str) -> None:
    """Print a section title in the terminal."""

    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def print_check(name: str, passed: bool, detail: str) -> None:
    """Print one validation check result."""

    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {name}: {detail}")


def get_single_count(connection, sql: str) -> int:
    """Run a SQL count query and return the count as a Python integer."""

    result = connection.execute(text(sql))
    return int(result.scalar_one())


def check_review_features_table_exists(connection) -> bool:
    """Check if the review_features table exists."""

    table_count = get_single_count(
        connection,
        """
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_schema = 'public'
            AND table_name = 'review_features';
        """,
    )

    passed = table_count == 1
    detail = (
        "review_features table found"
        if passed
        else "review_features table not found"
    )
    print_check("review_features table exists", passed, detail)
    return passed


def check_review_features_has_rows(connection) -> bool:
    """Check if the review_features table has any rows."""

    review_feature_count = get_single_count(
        connection,
        "SELECT COUNT(*) FROM review_features;",
    )

    passed = review_feature_count > 0
    print_check(
        "review_features row count greater than 0",
        passed,
        f"{review_feature_count} rows found",
    )
    return passed


def check_review_feature_count_matches_eligible_clean_reviews(connection) -> bool:
    """Check that review_features has one row for each eligible clean review."""

    review_feature_count = get_single_count(
        connection,
        "SELECT COUNT(*) FROM review_features;",
    )
    eligible_clean_review_count = get_single_count(
        connection,
        """
        SELECT COUNT(*)
        FROM clean_reviews
        WHERE cleaned_review_text IS NOT NULL
            AND TRIM(cleaned_review_text) <> '';
        """,
    )

    passed = review_feature_count == eligible_clean_review_count
    print_check(
        "review_features row count matches eligible clean_reviews row count",
        passed,
        (
            f"review_features={review_feature_count}, "
            f"eligible_clean_reviews={eligible_clean_review_count}"
        ),
    )
    return passed


def check_duplicate_review_ids(connection) -> bool:
    """Check that review_features does not contain duplicate review_id values."""

    duplicate_review_id_count = get_single_count(
        connection,
        """
        SELECT COUNT(*)
        FROM (
            SELECT review_id
            FROM review_features
            GROUP BY review_id
            HAVING COUNT(*) > 1
        ) duplicate_review_ids;
        """,
    )

    passed = duplicate_review_id_count == 0
    print_check(
        "Duplicate review_id values",
        passed,
        f"{duplicate_review_id_count} duplicate review_id values found",
    )
    return passed


def check_no_null_values(connection, column_name: str) -> bool:
    """Check that one review_features column has no NULL values."""

    null_count = get_single_count(
        connection,
        f"""
        SELECT COUNT(*)
        FROM review_features
        WHERE {column_name} IS NULL;
        """,
    )

    passed = null_count == 0
    print_check(
        f"NULL {column_name} values",
        passed,
        f"{null_count} NULL {column_name} values found",
    )
    return passed


def check_all_review_feature_ids_exist_in_clean_reviews(connection) -> bool:
    """Check that every review_features review_id exists in clean_reviews."""

    missing_clean_review_count = get_single_count(
        connection,
        """
        SELECT COUNT(*)
        FROM review_features
        LEFT JOIN clean_reviews
            ON review_features.review_id = clean_reviews.review_id
        WHERE clean_reviews.review_id IS NULL;
        """,
    )

    passed = missing_clean_review_count == 0
    print_check(
        "review_features.review_id values exist in clean_reviews",
        passed,
        f"{missing_clean_review_count} feature rows missing from clean_reviews",
    )
    return passed


def check_all_review_feature_app_ids_exist_in_apps(connection) -> bool:
    """Check that every review_features app_id exists in apps."""

    missing_app_count = get_single_count(
        connection,
        """
        SELECT COUNT(*)
        FROM review_features
        LEFT JOIN apps
            ON review_features.app_id = apps.app_id
        WHERE apps.app_id IS NULL;
        """,
    )

    passed = missing_app_count == 0
    print_check(
        "review_features.app_id values exist in apps",
        passed,
        f"{missing_app_count} feature rows reference app IDs missing from apps",
    )
    return passed


def check_nullable_value_range(
    connection,
    column_name: str,
    valid_condition: str,
    description: str,
) -> bool:
    """Check that NULL values are allowed and non-NULL values are in range."""

    invalid_count = get_single_count(
        connection,
        f"""
        SELECT COUNT(*)
        FROM review_features
        WHERE {column_name} IS NOT NULL
            AND NOT ({valid_condition});
        """,
    )

    passed = invalid_count == 0
    print_check(
        description,
        passed,
        f"{invalid_count} rows have invalid {column_name} values",
    )
    return passed


def check_boolean_indicator_columns_not_null(connection) -> bool:
    """Check that boolean indicator feature columns do not contain NULL values."""

    results = []

    for column_name in BOOLEAN_INDICATOR_COLUMNS:
        results.append(check_no_null_values(connection, column_name))

    return all(results)


def check_forbidden_columns_not_present(connection) -> bool:
    """Check that label and prediction columns are not in review_features."""

    result = connection.execute(
        text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
                AND table_name = 'review_features'
                AND column_name = ANY(:forbidden_columns)
            ORDER BY column_name;
            """
        ),
        {"forbidden_columns": FORBIDDEN_FEATURE_COLUMNS},
    )

    present_forbidden_columns = [
        row["column_name"]
        for row in result.mappings()
    ]

    passed = len(present_forbidden_columns) == 0
    detail = (
        "0 forbidden label or prediction columns found"
        if passed
        else (
            "Forbidden columns found: "
            f"{', '.join(present_forbidden_columns)}"
        )
    )

    print_check(
        "Forbidden label and prediction columns are not present",
        passed,
        detail,
    )
    return passed


def main() -> bool:
    """Validate that review_features rows are safe and model-ready."""

    engine = get_database_engine()

    print_section("Review Features Validation Report")

    with engine.connect() as connection:
        table_exists = check_review_features_table_exists(connection)

        print_section("Critical Validation Checks")

        if not table_exists:
            print("Skipping remaining checks because review_features does not exist.")
            critical_results = [False]
        else:
            critical_results = [
                table_exists,
                check_review_features_has_rows(connection),
                check_review_feature_count_matches_eligible_clean_reviews(
                    connection,
                ),
                check_duplicate_review_ids(connection),
                check_no_null_values(connection, "review_id"),
                check_no_null_values(connection, "app_id"),
                check_all_review_feature_ids_exist_in_clean_reviews(connection),
                check_all_review_feature_app_ids_exist_in_apps(connection),
                check_nullable_value_range(
                    connection,
                    "rating",
                    "rating BETWEEN 1 AND 5",
                    "rating is NULL or between 1 and 5",
                ),
                check_nullable_value_range(
                    connection,
                    "day_of_week",
                    "day_of_week BETWEEN 0 AND 6",
                    "day_of_week is NULL or between 0 and 6",
                ),
                check_nullable_value_range(
                    connection,
                    "review_text_length",
                    "review_text_length >= 0",
                    "review_text_length is NULL or greater than or equal to 0",
                ),
                check_nullable_value_range(
                    connection,
                    "word_count",
                    "word_count >= 0",
                    "word_count is NULL or greater than or equal to 0",
                ),
                check_boolean_indicator_columns_not_null(connection),
                check_no_null_values(connection, "feature_set_version"),
                check_no_null_values(connection, "features_generated_at"),
                check_forbidden_columns_not_present(connection),
            ]

    all_validation_checks_passed = all(critical_results)

    print_section("Overall Status")

    if all_validation_checks_passed:
        print("OVERALL STATUS: PASS")
    else:
        print("OVERALL STATUS: FAIL")

    return all_validation_checks_passed


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
