import argparse
import csv
from pathlib import Path

from sqlalchemy import text

from src.database.connection import get_database_engine


DEFAULT_SAMPLE_SIZE = 50
OUTPUT_FILE_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "manual_labelling"
    / "manual_label_sample.csv"
)

CSV_COLUMNS = [
    "review_id",
    "app_id",
    "cleaned_review_text",
    "rating",
    "review_date",
    "weak_scope_label",
    "weak_primary_issue_label",
    "weak_rule_match_score",
    "manual_scope_label",
    "manual_primary_issue_label",
    "manual_priority_label",
    "label_notes",
]


def parse_arguments() -> argparse.Namespace:
    """Read command line arguments for the export script."""

    parser = argparse.ArgumentParser(
        description="Export a CSV sample for manually labelling clean reviews."
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=DEFAULT_SAMPLE_SIZE,
        help=f"Number of reviews to export. Default: {DEFAULT_SAMPLE_SIZE}",
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=OUTPUT_FILE_PATH,
        help=f"CSV file path to write. Default: {OUTPUT_FILE_PATH}",
    )

    return parser.parse_args()


def check_table_exists(connection, table_name: str) -> bool:
    """Check whether a database table exists in the public schema."""

    sql = text(
        """
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_schema = 'public'
            AND table_name = :table_name;
        """
    )

    table_count = connection.execute(sql, {"table_name": table_name}).scalar_one()
    return int(table_count) == 1


def fetch_manual_label_sample(
    connection,
    sample_size: int,
    manual_label_table_exists: bool,
) -> list[dict]:
    """Read a random sample of clean reviews and weak label hints."""

    manual_label_filter = ""
    manual_label_join = ""

    if manual_label_table_exists:
        manual_label_join = """
        LEFT JOIN review_labels_manual manual_labels
            ON clean_reviews.review_id = manual_labels.review_id
        """
        manual_label_filter = "AND manual_labels.review_id IS NULL"

    sql = text(
        f"""
        SELECT
            clean_reviews.review_id,
            clean_reviews.app_id,
            clean_reviews.cleaned_review_text,
            raw_reviews.rating,
            raw_reviews.review_date,
            weak_labels.scope_label AS weak_scope_label,
            weak_labels.issue_label AS weak_primary_issue_label,
            weak_labels.rule_match_score AS weak_rule_match_score,
            '' AS manual_scope_label,
            '' AS manual_primary_issue_label,
            '' AS manual_priority_label,
            '' AS label_notes
        FROM clean_reviews
        JOIN raw_reviews
            ON clean_reviews.review_id = raw_reviews.review_id
        LEFT JOIN review_labels_weak weak_labels
            ON clean_reviews.review_id = weak_labels.review_id
        {manual_label_join}
        WHERE clean_reviews.is_empty_text = FALSE
            {manual_label_filter}
        ORDER BY RANDOM()
        LIMIT :sample_size;
        """
    )

    result = connection.execute(sql, {"sample_size": sample_size})
    return [dict(row) for row in result.mappings()]


def write_sample_csv(rows: list[dict], output_path: Path) -> None:
    """Write manual labelling sample rows to a CSV file."""

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def export_manual_label_sample(sample_size: int, output_path: Path) -> int:
    """Export a random clean review sample for manual labelling."""

    if sample_size < 1:
        raise ValueError("sample-size must be 1 or greater.")

    engine = get_database_engine()

    with engine.connect() as connection:
        manual_label_table_exists = check_table_exists(
            connection,
            "review_labels_manual",
        )
        sample_rows = fetch_manual_label_sample(
            connection,
            sample_size,
            manual_label_table_exists,
        )

    write_sample_csv(sample_rows, output_path)
    return len(sample_rows)


def main() -> None:
    """Run the manual label sample export from the command line."""

    arguments = parse_arguments()
    exported_count = export_manual_label_sample(
        arguments.sample_size,
        arguments.output_path,
    )

    print("Manual labelling sample export complete.")
    print(f"Rows exported: {exported_count}")
    print(f"Output CSV path: {arguments.output_path}")
    print("Reminder: weak labels are hints only, not trusted truth.")


if __name__ == "__main__":
    main()
