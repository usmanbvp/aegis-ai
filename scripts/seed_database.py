from __future__ import annotations

import sys

sys.path.insert(0, "backend")

from app.database import initialize_database, seed_database


if __name__ == "__main__":
    session = initialize_database()
    try:
        stats = seed_database(session=session)
        print("Database seeded successfully:")
        for name, count in stats.items():
            print(f"- {name}: {count}")
    finally:
        session.close()
