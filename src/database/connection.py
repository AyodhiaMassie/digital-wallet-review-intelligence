import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, URL


def get_database_url() -> str:
    """Load local settings, then prefer DATABASE_URL over POSTGRES_* values."""

    # Resolve from this file so local commands work regardless of their cwd.
    load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)

    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    required_variables = ("POSTGRES_USER", "POSTGRES_PASSWORD")
    missing_variables = [name for name in required_variables if not os.getenv(name)]
    if missing_variables:
        raise ValueError(
            "Missing database environment variables: "
            + ", ".join(missing_variables)
            + ". Fill in the project .env file or set DATABASE_URL."
        )

    # URL.create safely escapes special characters in usernames and passwords.
    return URL.create(
        drivername="postgresql+psycopg2",
        username=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "digital_wallet_reviews"),
    ).render_as_string(hide_password=False)


# create reusable database engine
def get_database_engine() -> Engine:
    database_url = get_database_url()
    return create_engine(database_url)
