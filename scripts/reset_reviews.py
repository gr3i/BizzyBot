# scripts/reset_reviews.py
from sqlalchemy import inspect
from db.session import engine
from db.models import Base, Review, Reaction

def main():
    insp = inspect(engine)
    with engine.begin() as conn:
        # drop in correct order due to FK
        if insp.has_table(Reaction.__tablename__):
            Reaction.__table__.drop(conn, checkfirst=True)
        if insp.has_table(Review.__tablename__):
            Review.__table__.drop(conn, checkfirst=True)

        # create only these two tables
        Review.__table__.create(conn, checkfirst=True)
        Reaction.__table__.create(conn, checkfirst=True)

    print("Reviews schema recreated: hodnoceni, reakce")

if __name__ == "__main__":
    main()

