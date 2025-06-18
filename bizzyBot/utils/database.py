import sqlite3
import os

def create_connection():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_dir = os.path.join(base_dir, "..", "db")
    os.makedirs(db_dir, exist_ok=True)  # zajisti, ze slozka existuje
    db_path = os.path.join(db_dir, "verify.db")
    return sqlite3.connect(db_path)

def create_table():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS verifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        mail TEXT,
        verification_code TEXT,
        verified BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    conn.commit()
    conn.close()

