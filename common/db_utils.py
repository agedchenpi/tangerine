import psycopg2
import os

def connect_db(db_url):
    try:
        conn = psycopg2.connect(db_url)
        print("Connected to DB")
        return conn
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    db_url = os.getenv("DB_URL")
    if db_url:
        connect_db(db_url)
    else:
        print("DB_URL not set in environment")
