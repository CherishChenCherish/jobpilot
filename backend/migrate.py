"""Create all database tables. Run: python migrate.py"""

from dotenv import load_dotenv

load_dotenv()

from app import app
from models import db

with app.app_context():
    db.create_all()
    print("All tables created successfully.")

    # Verify tables exist
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    print(f"Tables in database: {tables}")
    for t in ["users", "searches", "subscriptions"]:
        if t in tables:
            print(f"  ✓ {t}")
        else:
            print(f"  ✗ {t} — MISSING")
