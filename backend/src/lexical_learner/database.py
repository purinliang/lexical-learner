# backend/src/lexical_learner/database.py
# Connect to PostgreSQL using DATABASE_URL and check the current database and user.

import os

import psycopg


def connect_database() -> psycopg.Connection:
    return psycopg.connect(os.environ["DATABASE_URL"])


if __name__ == "__main__":
    with connect_database() as connection:
        print(connection.execute("SELECT current_database(), current_user").fetchone())
