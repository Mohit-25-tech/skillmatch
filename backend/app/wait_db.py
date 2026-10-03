import time

from sqlalchemy import text

from app.db import engine

if __name__ == "__main__":
    for attempt in range(30):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            break
        except Exception:
            if attempt == 29:
                raise
            time.sleep(2)
