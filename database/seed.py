"""
seed.py
-------
Applies schema.sql to the Supabase PostgreSQL database.

Usage:
    python database/seed.py
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

load_dotenv()

SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "schema.sql")


def get_connection():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("[ERROR] DATABASE_URL not set in .env")
        sys.exit(1)
    return psycopg2.connect(db_url)


def apply_schema():
    print("=" * 60)
    print("  Horse Racing Platform — Database Setup")
    print("=" * 60)

    if not os.path.exists(SCHEMA_FILE):
        print(f"[ERROR] Schema file not found: {SCHEMA_FILE}")
        sys.exit(1)

    with open(SCHEMA_FILE, "r") as f:
        sql = f.read()

    print(f"\n  Connecting to database...")
    try:
        conn = get_connection()
        conn.autocommit = True
        cursor = conn.cursor()
        print("  Connected.\n")

        print("  Applying schema...")
        cursor.execute(sql)
        print("  Schema applied successfully.\n")

        # Verify tables were created
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = [row[0] for row in cursor.fetchall()]

        print("  Tables found in database:")
        for table in tables:
            print(f"    ✓ {table}")

        cursor.close()
        conn.close()

        print()
        print("=" * 60)
        print("  Setup complete.")
        print("=" * 60)

    except Exception as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    apply_schema()