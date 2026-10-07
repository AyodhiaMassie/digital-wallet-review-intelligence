from sqlalchemy import text

from src.database.connection import get_database_engine

# print formatting in terminal
def print_section(title: str) -> None:
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)

# format the printed out message in the terminal when we are doing a specific check 
def print_check(name: str, passed: bool, detail: str) -> None:
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {name}: {detail}")

# helper function to convert the returned count number by sql into 
# python readable 
def get_single_count(connection, sql: str) -> int:
    result = connection.execute(text(sql))
    return int(result.scalar_one())

def check_clean_reviews_table_exists(connection) -> bool:
    """check if the clean_reviews table exists"""

    table_count = get_single_count(
        connection,
        """
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_schema = 'public'
            AND table_name = 'clean_reviews';
        """,
    )

    passed = table_count == 1
    detail = "clean_reviews table found" if passed else "clean_reviews table not found"
    print_check("clean_reviews table exists", passed, detail)
    return passed


def check_clean_reviews_has_rows(connection) -> bool:
    """check if the clean_reviews table has any existing rows"""

    # get number of rows in clean_reviews table
    clean_review_count = get_single_count(
        connection,
        "SELECT COUNT(*) FROM clean_reviews;",
    )

    # set passed to true if row count in clean_reviews is > 0
    # false otherwise
    passed = clean_review_count > 0

    # print out the results of the check
    print_check(
        "clean_reviews row count greater than 0",
        passed,
        f"{clean_review_count} rows found",
    )

    return passed


def check_duplicate_review_ids(connection) -> bool:
    """get number of duplicate review_ids in the clean_reviews table"""
    
    duplicate_review_id_count = get_single_count(
        connection,
        """
        SELECT COUNT(*)
        FROM (
            SELECT review_id
            FROM clean_reviews
            GROUP BY review_id
            HAVING COUNT(*) > 1
        ) duplicate_review_ids;
        """,
    )

    # set passed to true if there are no duplicates
    # false otherwise
    passed = duplicate_review_id_count == 0
    
    # print out the check
    print_check(
        "Duplicate review_id values",
        passed,
        f"{duplicate_review_id_count} duplicate review_id values found",
    )
    return passed


def check_no_null_values(connection, column_name: str) -> bool:
    """get number of rows in clean_reviews where the specified column is null"""
    
    null_count = get_single_count(
        connection,
        f"""
        SELECT COUNT(*)
        FROM clean_reviews
        WHERE {column_name} IS NULL;
        """,
    )

    # set passed to true if there are no null values in the specified column
    passed = null_count == 0
    
    # print the results of the check
    print_check(
        f"NULL {column_name} values",
        passed,
        f"{null_count} NULL {column_name} values found",
    )
    return passed


def check_no_negative_values(connection, column_name: str) -> bool:
    """
    check that there are no negative values in the specified column
    """

    negative_count = get_single_count(
        connection,
        f"""
        SELECT COUNT(*)
        FROM clean_reviews
        WHERE {column_name} < 0;
        """,
    )

    # set passed to true if there are no negative values in the specified column
    passed = negative_count == 0
    
    # print out the results of the check
    print_check(
        f"Negative {column_name} values",
        passed,
        f"{negative_count} negative {column_name} values found",
    )
    return passed


def check_all_clean_review_ids_exist_in_raw_reviews(connection) -> bool:
    """
    check that all the review_ids were succesfully transferred from
    the raw_reviews to the clean_reviews table
    """
    
    missing_raw_review_count = get_single_count(
        connection,
        """
        SELECT COUNT(*)
        FROM clean_reviews
        LEFT JOIN raw_reviews
            ON clean_reviews.review_id = raw_reviews.review_id
        WHERE raw_reviews.review_id IS NULL;
        """,
    )

    # set passed to true if there are any reviews in the raw_reviews
    # that is missing from the clean_reviews
    passed = missing_raw_review_count == 0
    
    # print the results of the check
    print_check(
        "clean_reviews.review_id values exist in raw_reviews",
        passed,
        f"{missing_raw_review_count} clean reviews missing from raw_reviews",
    )
    return passed


def check_clean_review_count_matches_raw_review_count(connection) -> bool:
    
    """
    check that the number of rows in clean_reviews matches the number
    of rows in raw_reviews
    """

    # get number of rows in clean_reviews
    clean_review_count = get_single_count(
        connection,
        "SELECT COUNT(*) FROM clean_reviews;",
    )

    # get number of rows in raw_reviews
    raw_review_count = get_single_count(
        connection,
        "SELECT COUNT(*) FROM raw_reviews;",
    )

    # set passed = true if the number of rows in clean_reviews is
    # equal to the number of rows in raw_reviews
    passed = clean_review_count == raw_review_count
    print_check(
        "clean_reviews row count matches raw_reviews row count",
        passed,
        f"clean_reviews={clean_review_count}, raw_reviews={raw_review_count}",
    )
    return passed


def main() -> bool:

    # connect to database
    engine = get_database_engine()

    # print out the title of the validation report
    print_section("Clean Reviews Validation Report")

    # 
    with engine.connect() as connection:
        
        # check if the clean_reviews table exists, returns True or False
        table_exists = check_clean_reviews_table_exists(connection)

        # prints out section title of the validation report
        print_section("Critical Validation Checks")

        # if the clean_reviews table does not exist, we skip all the checks
        if not table_exists:
            print("Skipping remaining checks because clean_reviews does not exist.")
            critical_results = [False]

        # if the clean_reviews table exists, proceed with the checks
        else:

            # create list which contains boolean values that correspond to 
            # the result of the check
            critical_results = [
                table_exists,
                check_clean_reviews_has_rows(connection),
                check_duplicate_review_ids(connection),
                check_no_null_values(connection, "review_id"),
                check_no_null_values(connection, "app_id"),
                check_no_null_values(connection, "cleaned_review_text"),
                check_no_negative_values(connection, "word_count"),
                check_no_negative_values(connection, "review_text_length"),
                check_all_clean_review_ids_exist_in_raw_reviews(connection),
                check_clean_review_count_matches_raw_review_count(connection),
            ]

    # checks whether every value in critical_results list is true meaning
    # all validation checks were passed
    all_validation_checks_passed = all(critical_results)

    # print section title
    print_section("Overall Status")
    
    # if all validation checks were passed, print STATUS: PASS
    if all_validation_checks_passed:
        print("OVERALL STATUS: PASS")

    # if there is a fail in the checks, print STATUS: FAIL
    else:
        print("OVERALL STATUS: FAIL")

    # return the result of whether all validation checks were passed
    return all_validation_checks_passed


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
