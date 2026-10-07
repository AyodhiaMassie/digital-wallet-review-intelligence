from sqlalchemy import text

from src.database.connection import get_database_engine


REQUIRED_RAW_REVIEW_FIELDS = [
    "review_id",
    "app_id",
    "app_name",
    "rating",
    "review_date",
    "scraped_at",
    "source",
    "ingestion_run_id",
]


def print_section(title: str) -> None:
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def print_check(name: str, passed: bool, detail: str) -> None:
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {name}: {detail}")


def get_single_count(connection, sql: str) -> int:
    result = connection.execute(text(sql))
    return int(result.scalar_one())


def print_review_counts_by_app(connection) -> None:
    sql = text(
        """
        SELECT
            raw_reviews.app_id,
            raw_reviews.app_name,
            COUNT(*) AS review_count
        FROM raw_reviews
        GROUP BY raw_reviews.app_id, raw_reviews.app_name
        ORDER BY review_count DESC, raw_reviews.app_name;
        """
    )

    rows = connection.execute(sql).fetchall()

    print_section("Review Counts By App")

    if not rows:
        print("No reviews found in raw_reviews.")
        return

    for row in rows:
        print(
            f"{row.app_name} ({row.app_id}): "
            f"{row.review_count} reviews"
        )


def print_latest_ingestion_runs(connection, limit: int = 10) -> None:
    sql = text(
        """
        SELECT
            ingestion_runs.run_id,
            ingestion_runs.app_id,
            apps.app_name,
            ingestion_runs.status,
            ingestion_runs.started_at,
            ingestion_runs.ended_at,
            ingestion_runs.reviews_requested,
            ingestion_runs.reviews_collected,
            ingestion_runs.new_reviews_inserted,
            ingestion_runs.duplicates_skipped
        FROM ingestion_runs
        LEFT JOIN apps
            ON ingestion_runs.app_id = apps.app_id
        ORDER BY ingestion_runs.started_at DESC
        LIMIT :limit;
        """
    )

    rows = connection.execute(sql, {"limit": limit}).fetchall()

    print_section("Latest Ingestion Runs")

    if not rows:
        print("No ingestion runs found.")
        return

    for row in rows:
        app_name = row.app_name or "Unknown app"
        print(
            f"Run {row.run_id} | {app_name} ({row.app_id}) | "
            f"status={row.status} | started={row.started_at} | "
            f"ended={row.ended_at} | requested={row.reviews_requested} | "
            f"collected={row.reviews_collected} | "
            f"inserted={row.new_reviews_inserted} | "
            f"duplicates={row.duplicates_skipped}"
        )


def check_duplicate_review_ids(connection) -> bool:
    duplicate_review_id_count = get_single_count(
        connection,
        """
        SELECT COUNT(*)
        FROM (
            SELECT review_id
            FROM raw_reviews
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


def check_missing_required_fields(connection) -> bool:
    checks = []

    for field_name in REQUIRED_RAW_REVIEW_FIELDS:
        if field_name in {"review_id", "app_id", "app_name", "source"}:
            missing_condition = (
                f"{field_name} IS NULL OR TRIM({field_name}) = ''"
            )
        else:
            missing_condition = f"{field_name} IS NULL"

        sql = f"""
        SELECT COUNT(*)
        FROM raw_reviews
        WHERE {missing_condition};
        """

        missing_count = get_single_count(connection, sql)
        checks.append((field_name, missing_count))

    total_missing_values = sum(missing_count for _, missing_count in checks)
    passed = total_missing_values == 0

    detail_parts = [
        f"{field_name}={missing_count}"
        for field_name, missing_count in checks
    ]
    detail = ", ".join(detail_parts)

    print_check(
        "Missing required raw_reviews fields",
        passed,
        detail,
    )
    return passed


def check_invalid_ratings(connection) -> bool:
    invalid_rating_count = get_single_count(
        connection,
        """
        SELECT COUNT(*)
        FROM raw_reviews
        WHERE rating IS NULL OR rating < 1 OR rating > 5;
        """,
    )

    passed = invalid_rating_count == 0
    print_check(
        "Invalid ratings",
        passed,
        f"{invalid_rating_count} rows have ratings outside 1 to 5",
    )
    return passed


def check_unknown_app_ids(connection) -> bool:
    unknown_app_id_count = get_single_count(
        connection,
        """
        SELECT COUNT(*)
        FROM raw_reviews
        LEFT JOIN apps
            ON raw_reviews.app_id = apps.app_id
        WHERE apps.app_id IS NULL;
        """,
    )

    passed = unknown_app_id_count == 0
    print_check(
        "Unknown raw_reviews.app_id values",
        passed,
        f"{unknown_app_id_count} rows reference app IDs missing from apps",
    )
    return passed


def main() -> bool:
    engine = get_database_engine()

    print_section("Ingestion Database Checkpoint Report")

    with engine.connect() as connection:
        raw_review_count = get_single_count(
            connection,
            "SELECT COUNT(*) FROM raw_reviews;",
        )
        ingestion_run_count = get_single_count(
            connection,
            "SELECT COUNT(*) FROM ingestion_runs;",
        )

        print(f"raw_reviews rows: {raw_review_count}")
        print(f"ingestion_runs rows: {ingestion_run_count}")

        print_section("Critical Validation Checks")

        critical_results = [
            check_duplicate_review_ids(connection),
            check_missing_required_fields(connection),
            check_invalid_ratings(connection),
            check_unknown_app_ids(connection),
        ]

        print_review_counts_by_app(connection)
        print_latest_ingestion_runs(connection)

    all_critical_checks_passed = all(critical_results)

    print_section("Overall Status")
    if all_critical_checks_passed:
        print("OVERALL STATUS: PASS")
    else:
        print("OVERALL STATUS: FAIL")

    return all_critical_checks_passed


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
