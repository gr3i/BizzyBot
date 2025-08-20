# db/migrate_from_sqlite.py
import sqlite3
from datetime import datetime
from pathlib import Path

from db.session import engine, SessionLocal
from db.models import Base, Verification
# Pokud mam uz pripravene modely pro reviews:
# from db.models import Review, Reaction

SRC_VERIFY = Path("db/verify.db")
SRC_REVIEWS = Path("db/reviews.db")

def parse_dt(val):
    """Zkusi prevest 'YYYY-MM-DD HH:MM:SS' -> datetime; kdyz to nejde, vrat None."""
    if not val:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
        try:
            return datetime.strptime(val, fmt)
        except ValueError:
            continue
    try:
        # nekdy SQLite vrati uz ISO format
        return datetime.fromisoformat(val.replace("Z", ""))
    except Exception:
        return None

def migrate_verifications():
    if not SRC_VERIFY.exists():
        print("db/verify.db nenalezen – přeskočeno.")
        return
    # vytvor cilove tabulky
    Base.metadata.create_all(engine)

    src = sqlite3.connect(str(SRC_VERIFY))
    c = src.cursor()

    # overim, ze tabulka existuje
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='verifications'")
    if not c.fetchone():
        print("Tabulka 'verifications' ve staré DB neexistuje – přeskočeno.")
        return

    c.execute("SELECT id, user_id, mail, verification_code, verified, created_at FROM verifications")
    rows = c.fetchall()
    print(f"Nalezeno {len(rows)} záznamů ve 'verifications'.")

    migrated = 0
    with SessionLocal() as s:
        for r in rows:
            v = Verification(
                id=r[0],
                user_id=r[1],
                mail=r[2],
                verification_code=r[3],
                verified=bool(r[4]),
            )
            # pokud chci zachovat i created_at, pridam sloupec do modelu jako server_default + nullable=True
            # a tady nastavim:
            ca = parse_dt(r[5])
            if ca:
                # SQLAlchemy 2.x: pri explicitnim nastaveni to ulozim
                setattr(v, "created_at", ca)

            # merge zajisti, ze kdyz existuje stejne id, udela UPDATE; jinak INSERT
            s.merge(v)
            migrated += 1
        s.commit()
    print(f"Migrace 'verifications' hotová: {migrated} záznamů.")

def migrate_reviews():
    if not SRC_REVIEWS.exists():
        print("db/reviews.db nenalezen – přeskočeno.")
        return

    # TODO: odkomentuji a upravim, az budu mit modely Review/Reaction:
    """
    Base.metadata.create_all(engine)
    src = sqlite3.connect(str(SRC_REVIEWS))
    c = src.cursor()

    # Zjisti dostupné tabulky
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    print('Tabulky v reviews.db:', [t[0] for t in c.fetchall()])

    # ---- příklad, přizpůsob názvům/sloupcům ----
    c.execute("SELECT id, user_id, subject, text, created_at FROM hodnoceni")
    reviews = c.fetchall()
    with SessionLocal() as s:
        for r in reviews:
            obj = Review(
                id=r[0], user_id=r[1], subject=r[2], text=r[3]
            )
            ca = parse_dt(r[4])
            if ca:
                setattr(obj, "created_at", ca)
            s.merge(obj)
        s.commit()

    c.execute("SELECT id, hodnoceni_id, user_id, typ, created_at FROM reakce")
    reacts = c.fetchall()
    with SessionLocal() as s:
        for r in reacts:
            obj = Reaction(
                id=r[0], review_id=r[1], user_id=r[2], type=r[3]
            )
            ca = parse_dt(r[4])
            if ca:
                setattr(obj, "created_at", ca)
            s.merge(obj)
        s.commit()
    print("Migrace reviews hotová.")
    """

if __name__ == "__main__":
    migrate_verifications()
    migrate_reviews()

