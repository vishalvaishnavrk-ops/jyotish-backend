import os
import psycopg2

def get_db():
    database_url = os.environ.get("DATABASE_URL")

    conn = psycopg2.connect(
        database_url,
        sslmode="require"
    )

    return conn
