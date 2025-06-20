import sqlite3
import os

def create_connection():
    base_dir = os.path.dirname(os.path.abspath(__file__))  # ziska zakladni adresar
    db_dir = os.path.join(base_dir, "..", "db")  # sestavi cestu k db slozce
    os.makedirs(db_dir, exist_ok=True)  # vytvori slozku db, pokud jeste neexistuje
    db_path = os.path.join(db_dir, "verify.db")  # sestavi cestu k souboru verify.db
    return sqlite3.connect(db_path)  # vytvori spojeni se souborem db


def setup_database():
    """Vytvoření tabulky pro ověřování, pokud neexistuje."""
    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS verifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        mail TEXT,
        verification_code TEXT,
        verified BOOLEAN DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()
    conn.close()

# zavolani funkce setup_database pri spusteni aplikace
if __name__ == "__main__":
    setup_database()

