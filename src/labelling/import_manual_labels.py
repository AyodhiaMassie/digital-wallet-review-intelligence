import argparse
import csv
from pathlib import Path

from sqlalchemy import text
import yaml

from src.database.connection import get_database_engine


DEFAULT_CSV_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "manual_labelling"
    / "manual_label_sample.csv"
)
ISSUE_TAXONOMY_FILE_PATH = (
    Path(__file__).resolve().parents[2] / "config" / "issue_taxonomy.yaml"
)

REQUIRED_CSV_COLUMNS = [
    "review_id",
    "manual_scope_label",
    "manual_primary_issue_label",
    "manual_priority_label",
    "label_notes",
]

VALID_SCOPE_LABELS = {
    "wallet_related",
    "non_wallet_related",
    "unclear",
}
VALID_PRIORITY_LABELS = {
    "high",
    "medium",
    "low",
    "unclear",
}


def parse_arguments() -> argparse.Namespace:
    """Read command line arguments for the import script."""

    parser = argparse.ArgumentParser(
        description="Import completed manual review labels from a CSV file."
    )
    parser.add_argument(
        "--csv-path",
        type=Path,
        default=DEFAULT_CSV_PATH,
        help=f"CSV file to import. Default: {DEFAULT_CSV_PATH}",
    )
    parser.add_argument(
        "--labelled-by",
        default=None,
        help="Name or identifier of the person who created the manual labels.",
    )

    return parser.parse_args()


def load_allowed_issue_labels() -> set[str]:
    """Load allowed issue labels from config/issue_taxonomy.yaml."""

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


def clean_csv_value(row: dict, column_name: str) -> str:
    """Read and trim one CSV value."""

    value = row.get(column_name, "")

    if value is None:
        return ""

    return str(value).strip()


def read_csv_rows(csv_path: Path) -> list[dict]:
    """Read manual label CSV rows as dictionaries."""

    if not csv_path.exists():
        raise FileNotFoundError(f"Manual labels CSV not found: {csv_path}")

    with csv_path.open("r", newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)

        if reader.fieldnames is None:
            raise ValueError("Manual labels CSV is empty or has no header row.")

        missing_columns = [
            column_name
            for column_name in REQUIRED_CSV_COLUMNS
            if column_name not in reader.fieldnames
        ]
        if missing_columns:
            raise ValueError(
                "Manual labels CSV is missing required columns: "
                + ", ".join(missing_columns)
            )

        return [dict(row) for row in reader]


def prepare_manual_labels(
    csv_rows: list[dict],
    allowed_issue_labels: set[str],
    labelled_by: str | None,
) -> tuple[list[dict], int, list[str]]:
    """Validate CSV rows and prepare completed labels for database import."""

    manual_labels = []
    skipped_blank_count = 0
    validation_errors = []

    for row_number, row in enumerate(csv_rows, start=2):
        review_id = clean_csv_value(row, "review_id")
        scope_label = clean_csv_value(row, "manual_scope_label")
        primary_issue_label = clean_csv_value(row, "manual_primary_issue_label")
        priority_label = clean_csv_value(row, "manual_priority_label")
        label_notes = clean_csv_value(row, "label_notes")

        manual_values = [
            scope_label,
            primary_issue_label,
            priority_label,
            label_notes,
        ]
        required_manual_values = [
            scope_label,
            primary_issue_label,
            priority_label,
        ]

        if not any(manual_values):
            skipped_blank_count += 1
            continue

        if not review_id:
            validation_errors.append(f"Row {row_number}: review_id is blank.")

        if not all(required_manual_values):
            validation_errors.append(
                f"Row {row_number}: scope, primary issue, and priority "
                "must all be filled when importing a manual label."
            )

        if scope_label and scope_label not in VALID_SCOPE_LABELS:
            validation_errors.append(
                f"Row {row_number}: invalid manual_scope_label '{scope_label}'."
            )

        if priority_label and priority_label not in VALID_PRIORITY_LABELS:
            validation_errors.append(
                f"Row {row_number}: invalid manual_priority_label "
                f"'{priority_label}'."
            )

        if primary_issue_label and primary_issue_label not in allowed_issue_labels:
            validation_errors.append(
                f"Row {row_number}: invalid manual_primary_issue_label "
                f"'{primary_issue_label}'."
            )

        if (
            review_id
            and scope_label
            and primary_issue_label
            and priority_label
            and scope_label in VALID_SCOPE_LABELS
            and priority_label in VALID_PRIORITY_LABELS
            and primary_issue_label in allowed_issue_labels
        ):
            manual_labels.append(
                {
                    "review_id": review_id,
                    "scope_label": scope_label,
                    "primary_issue_label": primary_issue_label,
                    "priority_label": priority_label,
                    "labelled_by": labelled_by,
                    "label_notes": label_notes or None,
                }
            )

    return manual_labels, skipped_blank_count, validation_errors


def fetch_existing_clean_review_ids(connection, review_ids: list[str]) -> set[str]:
    """Return the review_ids that already exist in clean_reviews."""

    if not review_ids:
        return set()

    sql = text(
        """
        SELECT review_id
        FROM clean_reviews
        WHERE review_id = ANY(:review_ids);
        """
    )

    result = connection.execute(sql, {"review_ids": review_ids})
    return {row["review_id"] for row in result.mappings()}


def validate_review_ids_exist(connection, manual_labels: list[dict]) -> list[str]:
    """Check that every manual label review_id exists in clean_reviews."""

    review_ids = [manual_label["review_id"] for manual_label in manual_labels]
    existing_review_ids = fetch_existing_clean_review_ids(connection, review_ids)

    return [
        f"review_id '{review_id}' does not exist in clean_reviews."
        for review_id in review_ids
        if review_id not in existing_review_ids
    ]


def upsert_manual_labels(connection, manual_labels: list[dict]) -> int:
    """Insert manual labels, or update them if they already exist."""

    if not manual_labels:
        return 0

    sql = text(
        """
        INSERT INTO review_labels_manual (
            review_id,
            scope_label,
            primary_issue_label,
            priority_label,
            labelled_by,
            label_notes
        )
        VALUES (
            :review_id,
            :scope_label,
            :primary_issue_label,
            :priority_label,
            :labelled_by,
            :label_notes
        )
        ON CONFLICT (review_id) DO UPDATE
        SET
            scope_label = EXCLUDED.scope_label,
            primary_issue_label = EXCLUDED.primary_issue_label,
            priority_label = EXCLUDED.priority_label,
            labelled_by = EXCLUDED.labelled_by,
            label_notes = EXCLUDED.label_notes,
            labelled_at = now(),
            updated_at = now();
        """
    )

    inserted_or_updated_count = 0

    for manual_label in manual_labels:
        result = connection.execute(sql, manual_label)
        inserted_or_updated_count += result.rowcount

    return inserted_or_updated_count


def import_manual_labels(csv_path: Path, labelled_by: str | None) -> dict:
    """Validate and import completed manual labels from a CSV file."""

    if labelled_by is not None:
        labelled_by = labelled_by.strip() or None

    allowed_issue_labels = load_allowed_issue_labels()
    csv_rows = read_csv_rows(csv_path)

    manual_labels, skipped_blank_count, validation_errors = prepare_manual_labels(
        csv_rows,
        allowed_issue_labels,
        labelled_by,
    )

    inserted_or_updated_count = 0

    if not validation_errors and manual_labels:
        engine = get_database_engine()

        with engine.begin() as connection:
            validation_errors.extend(
                validate_review_ids_exist(connection, manual_labels)
            )

            if not validation_errors:
                inserted_or_updated_count = upsert_manual_labels(
                    connection,
                    manual_labels,
                )

    return {
        "rows_read": len(csv_rows),
        "rows_skipped_blank": skipped_blank_count,
        "rows_inserted_or_updated": inserted_or_updated_count,
        "validation_errors": validation_errors,
    }


def print_import_summary(summary: dict) -> None:
    """Print a beginner-readable import summary."""

    print("Manual labels import summary")
    print(f"Rows read: {summary['rows_read']}")
    print(
        "Rows skipped because manual labels were blank: "
        f"{summary['rows_skipped_blank']}"
    )
    print(f"Rows inserted or updated: {summary['rows_inserted_or_updated']}")

    validation_errors = summary["validation_errors"]

    if validation_errors:
        print()
        print("Validation errors:")
        for validation_error in validation_errors:
            print(f"- {validation_error}")
        print()
        print("No manual labels were imported because validation errors were found.")
    else:
        print("Validation errors: 0")


def main() -> None:
    """Run the manual label CSV import from the command line."""

    arguments = parse_arguments()
    summary = import_manual_labels(arguments.csv_path, arguments.labelled_by)
    print_import_summary(summary)


if __name__ == "__main__":
    main()
