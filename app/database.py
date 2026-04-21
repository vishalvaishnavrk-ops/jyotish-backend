import psycopg2
import os

DATABASE_URL = os.getenv("DATABASE_URL")

# 🔥 GLOBAL CONNECTION (REUSE)
conn = None

def get_db():
    global conn

    if conn is None or conn.closed != 0:
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")

    return conn
