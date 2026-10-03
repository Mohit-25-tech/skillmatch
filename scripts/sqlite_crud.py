"""Run a complete, parameterized SQLite CRUD demonstration with no dependencies."""

import sqlite3


def main() -> None:
    with sqlite3.connect(":memory:") as connection:
        connection.execute(
            "CREATE TABLE jobs (id INTEGER PRIMARY KEY, title TEXT NOT NULL, company TEXT NOT NULL, salary INTEGER NOT NULL CHECK(salary >= 0))"
        )
        cursor = connection.execute(
            "INSERT INTO jobs(title, company, salary) VALUES (?, ?, ?)",
            ("Python Engineer", "SkillMatch Studio", 120000),
        )
        job_id = cursor.lastrowid
        print("CREATE:", job_id)
        print(
            "READ:",
            connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone(),
        )
        connection.execute("UPDATE jobs SET salary = ? WHERE id = ?", (135000, job_id))
        print(
            "UPDATE:",
            connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone(),
        )
        connection.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        remaining = connection.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        assert remaining == 0
        print("DELETE: rows remaining =", remaining)


if __name__ == "__main__":
    main()
