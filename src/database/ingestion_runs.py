from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.database.connection import get_database_engine

# gets the current time in utc
def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

def create_ingestion_run(
    app_id: str,
    reviews_requested: int,
    source: str = "google_play",
) -> int:
    db_engine = get_database_engine()
    
    """
    add new row into ingestion_runs table when a new ingestion run occurs
    and return the ingestion runs run_id
    """

    # define sql query to add row into ingestion_runs table
    # :source, :app_id, etc are placeholder values for those columns that will get filled when the ingestion run finishes
    query = text(
        """
        INSERT INTO ingestion_runs (
            source,
            app_id,
            started_at,
            reviews_requested,
            status
        )
        VALUES (
            :source, 
            :app_id,
            :started_at,
            :reviews_requested,
            :status
        )
        RETURNING run_id;
        """
    )

    # dictionary storing values to bind the placeholder values
    placeholder_bind = {
        "source": source,
        "app_id": app_id,
        "started_at": _utc_now(),
        "reviews_requested": reviews_requested,
        "status": "running",
    }

    # opens database connection -> if everything works, commit. if something fails, rollback
    with db_engine.begin() as connection:
        
        # run the sql query and use the placeholder_bind dictionary to bind the placeholder values 
        # returns a result object
        result = connection.execute(query, placeholder_bind)
        
        # return the run id
        return result.scalar_one()


def finish_ingestion_run(
    run_id: int, # specify which row to update
    reviews_collected: int,
    new_reviews_inserted: int,
    duplicates_skipped: int,
    status: str,
    errors: str | None = None,
) -> None:
    engine = get_database_engine() # get database engine

    """
    update the newly added ingestion run row

    """
    
    sql = text(
        """
        UPDATE ingestion_runs
        SET
            ended_at = :ended_at,
            reviews_collected = :reviews_collected,
            new_reviews_inserted = :new_reviews_inserted,
            duplicates_skipped = :duplicates_skipped,
            errors = :errors,
            status = :status
        WHERE run_id = :run_id;
        """
    )

    # dictionary containing values to bind the placeholders to
    placeholder_bind = {
        "run_id": run_id,
        "ended_at": _utc_now(),
        "reviews_collected": reviews_collected,
        "new_reviews_inserted": new_reviews_inserted,
        "duplicates_skipped": duplicates_skipped,
        "errors": errors,
            "status": status,
    }

    # run the sql query and bind the placeholder values to the placeholders
    with engine.begin() as connection:
        connection.execute(sql, placeholder_bind)