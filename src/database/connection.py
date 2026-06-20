import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

DEFAULT_DATABASE_URL = (
    "postgresql+psycopg2://postgres:postgres@localhost:5432/"
    "digital_wallet_reviews"
)

# use DATABASE_URL env variable if it exists, otherwise use local Docker database
def get_database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)

# create reusable database engine
def get_database_engine() -> Engine:
    database_url = get_database_url()
    return create_engine(database_url)