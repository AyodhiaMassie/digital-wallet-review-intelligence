from pathlib import Path

from sqlalchemy import text
import yaml

from src.database.connection import get_database_engine


ISSUE_TAXONOMY_FILE_PATH = (
    Path(__file__).resolve().parents[2] / "config" / "issue_taxonomy.yaml"
)


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


def load_allowed_issue_labels() -> set[str]:
    """Load allowed primary issue labels from config/issue_taxonomy.yaml."""

    if not ISSUE_TAXONOMY_FILE_PATH.exists():
        raise FileNotFoundError(
            f"Issue taxonomy file not found: {ISSUE_TAXONOMY_FILE_PATH}"
        )

    with ISSUE_TAXONOMY_FILE_PATH.open("r", encoding="utf-8") as taxonomy_file:
        taxonomy = yaml.safe_load(taxonomy_file)

    if not isinstance(taxonomy, dict):
        raise ValueError("Issue taxonomy file must contain a YAML dictionary.")

    issue_categories = taxonomy.get("issue_categories", [])

    return {
        issue_category["label"]
        for issue_category in issue_categories
        if isinstance(issue_category, dict) and issue_category.get("label")
    }


def check_review_labels_manual_table_exists(connection) -> bool:
    """Check if the review_labels_manual table exists."""

    table_count = get_single_count(
        connection,
        """
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_schema = 'public'
            AND table_name = 'review_labels_manual';
        """,
    )

    passed = table_count == 1
    detail = (
        "review_labels_manual table found"
        if passed
        else "review_labels_manual table not found"
    )
    print_check("review_labels_manual table exists", passed, detail)
    return passed


def get_review_labels_manual_row_count(connection) -> int:
    """Count rows in review_labels_manual."""

    manual_label_count = get_single_count(
        connection,
        "SELECT COUNT(*) FROM review_labels_manual;",
    )

    print_check(
        "review_labels_manual row count",
        True,
        f"{manual_label_count} rows found",
    )
    return manual_label_count


def check_no_null_values(connection, column_name: str) -> bool:
    """Check that one review_labels_manual column has no NULL values."""

    null_count = get_single_count(
        connection,
        f"""
        SELECT COUNT(*)
        FROM review_labels_manual
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


def check_duplicate_review_ids(connection) -> bool:
    """Check that review_labels_manual does not contain duplicate review_id values."""

    duplicate_review_id_count = get_single_count(
        connection,
        """
        SELECT COUNT(*)
        FROM (
            SELECT review_id
            FROM review_labels_manual
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


def check_all_manual_label_review_ids_exist_in_clean_reviews(connection) -> bool:
    """Check that every manual label review_id exists in clean_reviews."""

    missing_clean_review_count = get_single_count(
        connection,
        """
        SELECT COUNT(*)
        FROM review_labels_manual
        LEFT JOIN clean_reviews
            ON review_labels_manual.review_id = clean_reviews.review_id
        WHERE clean_reviews.review_id IS NULL;
        """,
    )

    passed = missing_clean_review_count == 0
    print_check(
        "review_labels_manual.review_id values exist in clean_reviews",
        passed,
        f"{missing_clean_review_count} manual labels missing from clean_reviews",
    )
    return passed


def check_scope_label_values(connection) -> bool:
    """Check that scope_label only contains expected values."""

    invalid_scope_label_count = get_single_count(
        connection,
        """
        SELECT COUNT(*)
        FROM review_labels_manual
        WHERE scope_label NOT IN (
            'wallet_related',
            'non_wallet_related',
            'unclear'
        );
        """,
    )

    passed = invalid_scope_label_count == 0
    print_check(
        "scope_label values are valid",
        passed,
        f"{invalid_scope_label_count} rows have invalid scope_label values",
    )
    return passed


def check_priority_label_values(connection) -> bool:
    """Check that priority_label only contains expected values."""

    invalid_priority_label_count = get_single_count(
        connection,
        """
        SELECT COUNT(*)
        FROM review_labels_manual
        WHERE priority_label NOT IN (
            'high',
            'medium',
            'low',
            'unclear'
        );
        """,
    )

    passed = invalid_priority_label_count == 0
    print_check(
        "priority_label values are valid",
        passed,
        f"{invalid_priority_label_count} rows have invalid priority_label values",
    )
    return passed


def check_primary_issue_label_values(
    connection,
    allowed_issue_labels: set[str],
) -> bool:
    """Check that primary_issue_label values exist in issue_taxonomy.yaml."""

    result = connection.execute(
        text(
            """
            SELECT DISTINCT primary_issue_label
            FROM review_labels_manual
            WHERE primary_issue_label IS NOT NULL;
            """
        )
    )

    primary_issue_labels = [
        row["primary_issue_label"]
        for row in result.mappings()
    ]
    invalid_primary_issue_labels = [
        primary_issue_label
        for primary_issue_label in primary_issue_labels
        if primary_issue_label not in allowed_issue_labels
    ]

    passed = len(invalid_primary_issue_labels) == 0
    detail = (
        "0 rows have invalid primary_issue_label values"
        if passed
        else (
            f"{len(invalid_primary_issue_labels)} invalid primary_issue_label "
            f"values found: {', '.join(invalid_primary_issue_labels)}"
        )
    )

    print_check(
        "primary_issue_label values exist in issue_taxonomy.yaml",
        passed,
        detail,
    )
    return passed


def main() -> bool:
    """Validate that manual labels are ready for future model work."""

    allowed_issue_labels = load_allowed_issue_labels()
    engine = get_database_engine()

    print_section("Manual Labels Validation Report")

    with engine.connect() as connection:
        table_exists = check_review_labels_manual_table_exists(connection)

        print_section("Critical Validation Checks")

        if not table_exists:
            print("Skipping remaining checks because review_labels_manual does not exist.")
            critical_results = [False]
        else:
            manual_label_count = get_review_labels_manual_row_count(connection)

            if manual_label_count == 0:
                print()
                print(
                    "review_labels_manual has 0 rows. "
                    "This is acceptable for now because manual labelling "
                    "has not started yet."
                )
                critical_results = [table_exists]
            else:
                critical_results = [
                    table_exists,
                    check_no_null_values(connection, "review_id"),
                    check_no_null_values(connection, "scope_label"),
                    check_no_null_values(connection, "primary_issue_label"),
                    check_no_null_values(connection, "priority_label"),
                    check_no_null_values(connection, "labelled_at"),
                    check_duplicate_review_ids(connection),
                    check_all_manual_label_review_ids_exist_in_clean_reviews(
                        connection,
                    ),
                    check_scope_label_values(connection),
                    check_priority_label_values(connection),
                    check_primary_issue_label_values(
                        connection,
                        allowed_issue_labels,
                    ),
                ]

    all_validation_checks_passed = all(critical_results)

    print_section("Overall Status")

    if all_validation_checks_passed:
        print("OVERALL STATUS: PASS")
    else:
        print("OVERALL STATUS: FAIL")

    return all_validation_checks_passed


if __name__ == "__main__":
    main()
