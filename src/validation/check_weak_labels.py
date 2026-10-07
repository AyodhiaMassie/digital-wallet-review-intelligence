from sqlalchemy import text

from src.database.connection import get_database_engine


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


def check_review_labels_weak_table_exists(connection) -> bool:
    """Check if the review_labels_weak table exists."""

    table_count = get_single_count(
        connection,
        """
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_schema = 'public'
            AND table_name = 'review_labels_weak';
        """,
    )

    passed = table_count == 1
    detail = (
        "review_labels_weak table found"
        if passed
        else "review_labels_weak table not found"
    )
    print_check("review_labels_weak table exists", passed, detail)
    return passed


def check_review_labels_weak_has_rows(connection) -> bool:
    """Check if the review_labels_weak table has any rows."""

    weak_label_count = get_single_count(
        connection,
        "SELECT COUNT(*) FROM review_labels_weak;",
    )

    passed = weak_label_count > 0
    print_check(
        "review_labels_weak row count greater than 0",
        passed,
        f"{weak_label_count} rows found",
    )
    return passed


def check_weak_label_count_matches_clean_review_count(connection) -> bool:
    """Check that review_labels_weak has one row for each clean review."""

    weak_label_count = get_single_count(
        connection,
        "SELECT COUNT(*) FROM review_labels_weak;",
    )
    clean_review_count = get_single_count(
        connection,
        "SELECT COUNT(*) FROM clean_reviews;",
    )

    passed = weak_label_count == clean_review_count
    print_check(
        "review_labels_weak row count matches clean_reviews row count",
        passed,
        f"review_labels_weak={weak_label_count}, clean_reviews={clean_review_count}",
    )
    return passed


def check_duplicate_review_ids(connection) -> bool:
    """Check that review_labels_weak does not contain duplicate review_id values."""

    duplicate_review_id_count = get_single_count(
        connection,
        """
        SELECT COUNT(*)
        FROM (
            SELECT review_id
            FROM review_labels_weak
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
    """Check that one review_labels_weak column has no NULL values."""

    null_count = get_single_count(
        connection,
        f"""
        SELECT COUNT(*)
        FROM review_labels_weak
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


def check_all_weak_label_review_ids_exist_in_clean_reviews(connection) -> bool:
    """Check that every weak label review_id exists in clean_reviews."""

    missing_clean_review_count = get_single_count(
        connection,
        """
        SELECT COUNT(*)
        FROM review_labels_weak
        LEFT JOIN clean_reviews
            ON review_labels_weak.review_id = clean_reviews.review_id
        WHERE clean_reviews.review_id IS NULL;
        """,
    )

    passed = missing_clean_review_count == 0
    print_check(
        "review_labels_weak.review_id values exist in clean_reviews",
        passed,
        f"{missing_clean_review_count} weak labels missing from clean_reviews",
    )
    return passed


def check_rule_match_score_range(connection) -> bool:
    """Check that rule_match_score values are between 1 and 5."""

    invalid_score_count = get_single_count(
        connection,
        """
        SELECT COUNT(*)
        FROM review_labels_weak
        WHERE rule_match_score < 1
            OR rule_match_score > 5;
        """,
    )

    passed = invalid_score_count == 0
    print_check(
        "rule_match_score between 1 and 5",
        passed,
        f"{invalid_score_count} rows have rule_match_score outside 1 to 5",
    )
    return passed


def check_scope_label_values(connection) -> bool:
    """Check that scope_label only contains expected values."""

    invalid_scope_label_count = get_single_count(
        connection,
        """
        SELECT COUNT(*)
        FROM review_labels_weak
        WHERE scope_label NOT IN ('wallet_related', 'non_wallet_related');
        """,
    )

    passed = invalid_scope_label_count == 0
    print_check(
        "scope_label values are valid",
        passed,
        f"{invalid_scope_label_count} rows have invalid scope_label values",
    )
    return passed


def check_issue_label_not_empty(connection) -> bool:
    """Check that issue_label does not contain NULL or empty strings."""

    empty_issue_label_count = get_single_count(
        connection,
        """
        SELECT COUNT(*)
        FROM review_labels_weak
        WHERE issue_label IS NULL
            OR TRIM(issue_label) = '';
        """,
    )

    passed = empty_issue_label_count == 0
    print_check(
        "issue_label is not NULL or empty",
        passed,
        f"{empty_issue_label_count} rows have NULL or empty issue_label values",
    )
    return passed


def main() -> bool:
    """Validate that weak labels were inserted correctly."""

    engine = get_database_engine()

    print_section("Weak Labels Validation Report")

    with engine.connect() as connection:
        table_exists = check_review_labels_weak_table_exists(connection)

        print_section("Critical Validation Checks")

        if not table_exists:
            print("Skipping remaining checks because review_labels_weak does not exist.")
            critical_results = [False]
        else:
            critical_results = [
                table_exists,
                check_review_labels_weak_has_rows(connection),
                check_weak_label_count_matches_clean_review_count(connection),
                check_duplicate_review_ids(connection),
                check_no_null_values(connection, "review_id"),
                check_no_null_values(connection, "app_id"),
                check_no_null_values(connection, "scope_label"),
                check_no_null_values(connection, "issue_label"),
                check_no_null_values(connection, "rule_match_score"),
                check_no_null_values(connection, "label_version"),
                check_all_weak_label_review_ids_exist_in_clean_reviews(connection),
                check_rule_match_score_range(connection),
                check_scope_label_values(connection),
                check_issue_label_not_empty(connection),
                check_no_null_values(connection, "matched_scope_terms"),
                check_no_null_values(connection, "matched_issue_terms"),
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
