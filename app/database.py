import psycopg2
from psycopg2 import pool
import os

DATABASE_URL = os.getenv("DATABASE_URL")

# 🔥 PRODUCTION SAFE POOL
db_pool = psycopg2.pool.SimpleConnectionPool(
    minconn=1,
    maxconn=5,                # 🔥 IMPORTANT: 5 ही रखो (pooler friendly)
    dsn=DATABASE_URL,
    sslmode="require",
    connect_timeout=5,        # 🔥 fast fail (spinner नहीं घूमेगा)
    keepalives=1,
    keepalives_idle=30,
    keepalives_interval=10,
    keepalives_count=5
)

def get_db():
    return db_pool.getconn()

def release_db(conn):
    db_pool.putconn(conn)
