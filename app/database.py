import psycopg2
from psycopg2 import pool
import os

DATABASE_URL = os.getenv("DATABASE_URL")

# 🔥 CONNECTION POOL (MAIN FIX)
db_pool = psycopg2.pool.SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    dsn=DATABASE_URL,
    sslmode="require"
)

def get_db():
    return db_pool.getconn()

def release_db(conn):
    db_pool.putconn(conn)
