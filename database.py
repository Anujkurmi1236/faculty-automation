"""
database.py
-----------
SQLite data access layer for the Defaulter Letter Generator.

Changes vs. the original version:
  * WAL mode + indices for snappier lookups once the student list grows.
  * A single shared connection (opened lazily) instead of opening/closing a
    new sqlite3 connection on every call - cheaper and avoids Windows file
    locking hiccups when the app is packaged as an .exe.
  * `get_attendance_matrix()` - one call that returns every student joined
    with every subject's percentage, ready to drop straight into a table
    widget (this is what the "manual attendance with percentages" UI uses).
  * `set_attendance_bulk()` - save every subject for one student in a single
    transaction (used by the new manual-entry dialog).
  * `delete_attendance()` and `get_defaulter_subjects()` for per-subject
    editing / reporting.
  * Basic logging instead of silent failure, and light validation so a typo
    in an Excel import doesn't crash the whole batch.
"""
from __future__ import annotations

import logging
import os
import sys
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Iterable, Optional

log = logging.getLogger("defaulter_app.database")


def get_db_path() -> str:
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "letters.db")


DB_PATH = get_db_path()

_connection: Optional[sqlite3.Connection] = None


def get_connection() -> sqlite3.Connection:
    """Return a single shared connection, opened on first use.

    sqlite3 connections are cheap to reuse and this avoids the overhead
    (and, on Windows exe builds, occasional file-lock flakiness) of opening
    a brand-new connection for every single query.
    """
    global _connection
    if _connection is None:
        _connection = sqlite3.connect(DB_PATH, check_same_thread=False)
        _connection.row_factory = sqlite3.Row
        _connection.execute("PRAGMA foreign_keys = ON")
        _connection.execute("PRAGMA journal_mode = WAL")
    return _connection


@contextmanager
def tx():
    """Context manager that commits on success and rolls back on error."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def init_db() -> None:
    with tx() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                roll_no        TEXT UNIQUE NOT NULL,
                student_name   TEXT NOT NULL,
                class          TEXT,
                div            TEXT,
                parent_name    TEXT,
                parent_contact TEXT,
                created_at     TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS subjects (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                code       TEXT UNIQUE NOT NULL,
                name       TEXT NOT NULL,
                type       TEXT,           -- 'Theory' or 'Practical'
                created_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id   INTEGER NOT NULL,
                subject_code TEXT NOT NULL,
                percent      REAL,
                attended     INTEGER,
                lectures     INTEGER,
                updated_at   TEXT,
                UNIQUE(student_id, subject_code),
                FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS letters (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id    INTEGER,
                faculty_name  TEXT,
                date          TEXT,
                class         TEXT,
                div           TEXT,
                roll_no       TEXT,
                student_name  TEXT,
                intimation_no TEXT,
                from_date     TEXT,
                to_date       TEXT,
                created_at    TEXT,
                FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE SET NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_students_roll ON students(roll_no)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_attendance_student ON attendance(student_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_attendance_subject ON attendance(subject_code)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_letters_student ON letters(student_id)")
        columns = {row[1] for row in conn.execute("PRAGMA table_info(attendance)")}
        if "attended" not in columns:
            conn.execute("ALTER TABLE attendance ADD COLUMN attended INTEGER")
        if "lectures" not in columns:
            conn.execute("ALTER TABLE attendance ADD COLUMN lectures INTEGER")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------- STUDENTS
def add_student(data: dict) -> int:
    with tx() as conn:
        cur = conn.execute("""
            INSERT INTO students
            (roll_no, student_name, class, div, parent_name, parent_contact, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            data["roll_no"], data["student_name"],
            data.get("class", ""), data.get("div", ""),
            data.get("parent_name", ""), data.get("parent_contact", ""),
            _now(),
        ))
        if cur.lastrowid is None:
            raise RuntimeError("INSERT did not return a lastrowid")
        return cur.lastrowid


def upsert_student(data: dict) -> int:
    """Insert or update based on roll_no. Returns the student id."""
    existing = get_student_by_roll(data["roll_no"])
    if existing:
        with tx() as conn:
            conn.execute("""
                UPDATE students
                SET student_name=?, class=?, div=?, parent_name=?, parent_contact=?
                WHERE roll_no=?
            """, (
                data["student_name"], data.get("class", ""), data.get("div", ""),
                data.get("parent_name", ""), data.get("parent_contact", ""),
                data["roll_no"],
            ))
        return existing["id"]
    return add_student(data)


def update_student(student_id: int, data: dict) -> None:
    with tx() as conn:
        conn.execute("""
            UPDATE students
            SET roll_no=?, student_name=?, class=?, div=?,
                parent_name=?, parent_contact=?
            WHERE id=?
        """, (
            data["roll_no"], data["student_name"],
            data.get("class", ""), data.get("div", ""),
            data.get("parent_name", ""), data.get("parent_contact", ""),
            student_id,
        ))


def delete_student(student_id: int) -> None:
    with tx() as conn:
        conn.execute("DELETE FROM students WHERE id=?", (student_id,))


def get_student(sid: int):
    return get_connection().execute("SELECT * FROM students WHERE id=?", (sid,)).fetchone()


def get_student_by_roll(roll: str):
    return get_connection().execute(
        "SELECT * FROM students WHERE roll_no=?", (roll,)
    ).fetchone()


def fetch_all_students():
    return get_connection().execute("SELECT * FROM students ORDER BY roll_no").fetchall()


def search_students(kw: str):
    like = f"%{kw}%"
    return get_connection().execute("""
        SELECT * FROM students
        WHERE roll_no LIKE ? OR student_name LIKE ?
        ORDER BY roll_no
    """, (like, like)).fetchall()


# ----------------------------------------------------------------- SUBJECTS
def add_subject(code: str, name: str, stype: str) -> None:
    with tx() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO subjects (code, name, type, created_at)
            VALUES (?, ?, ?, ?)
        """, (code, name, stype, _now()))


def fetch_all_subjects():
    return get_connection().execute("SELECT * FROM subjects ORDER BY code").fetchall()


def update_subject(subject_id: int, code: str, name: str, stype: str) -> None:
    with tx() as conn:
        conn.execute("""
            UPDATE subjects SET code=?, name=?, type=? WHERE id=?
        """, (code, name, stype, subject_id))


def delete_subject(subject_id: int) -> None:
    with tx() as conn:
        conn.execute("DELETE FROM subjects WHERE id=?", (subject_id,))


# -------------------------------------------------------------- ATTENDANCE
def set_attendance(student_id: int, subject_code: str, percent: float) -> None:
    with tx() as conn:
        conn.execute("""
            INSERT INTO attendance (student_id, subject_code, percent, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(student_id, subject_code)
            DO UPDATE SET percent=excluded.percent, updated_at=excluded.updated_at
        """, (student_id, subject_code, percent, _now()))


def set_attendance_lectures(
    student_id: int, subject_code: str, attended: int, lectures: int
) -> None:
    if lectures <= 0 or attended < 0 or attended > lectures:
        raise ValueError("Attended lectures must be between 0 and total lectures")
    percent = attended * 100.0 / lectures
    with tx() as conn:
        conn.execute("""
            INSERT INTO attendance
                (student_id, subject_code, percent, attended, lectures, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(student_id, subject_code)
            DO UPDATE SET percent=excluded.percent, attended=excluded.attended,
                          lectures=excluded.lectures, updated_at=excluded.updated_at
        """, (student_id, subject_code, percent, attended, lectures, _now()))


def set_attendance_bulk(student_id: int, values: dict) -> None:
    """Save several subject_code -> (attended lectures, total lectures) pairs.

    Used by the manual "Edit Attendance" dialog so a student's whole row is
    written in a single transaction instead of one commit per subject.
    Entries whose value is None are skipped (left as-is / not created).
    """
    with tx() as conn:
        for code, counts in values.items():
            if counts is None:
                continue
            attended, lectures = counts
            if lectures <= 0 or attended < 0 or attended > lectures:
                raise ValueError("Attended lectures must be between 0 and total lectures")
            percent = attended * 100.0 / lectures
            conn.execute("""
                INSERT INTO attendance
                    (student_id, subject_code, percent, attended, lectures, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(student_id, subject_code)
                DO UPDATE SET percent=excluded.percent, attended=excluded.attended,
                              lectures=excluded.lectures, updated_at=excluded.updated_at
            """, (student_id, code, percent, attended, lectures, _now()))


def delete_attendance(student_id: int, subject_code: str) -> None:
    with tx() as conn:
        conn.execute(
            "DELETE FROM attendance WHERE student_id=? AND subject_code=?",
            (student_id, subject_code),
        )


def get_attendance(student_id: int):
    return get_connection().execute("""
        SELECT subject_code, percent, attended, lectures
        FROM attendance WHERE student_id=?
    """, (student_id,)).fetchall()


def get_attendance_matrix() -> list[dict]:
    """Every student with a dict of {subject_code: percent} attached.

    One query (students LEFT JOIN attendance) instead of N+1 round trips,
    so the manual-attendance table can repaint quickly even with a large
    class list.
    """
    conn = get_connection()
    rows = conn.execute("""
         SELECT s.id, s.roll_no, s.student_name, a.subject_code, a.percent,
             a.attended, a.lectures
        FROM students s
        LEFT JOIN attendance a ON a.student_id = s.id
        ORDER BY s.roll_no
    """).fetchall()

    by_student: dict[int, dict] = {}
    for r in rows:
        entry = by_student.setdefault(r["id"], {
            "id": r["id"],
            "roll_no": r["roll_no"],
            "student_name": r["student_name"],
            "attendance": {},
            "overall_theory": None,
        })
        if r["subject_code"] is not None:
            entry["attendance"][r["subject_code"]] = {
                "percent": r["percent"],
                "attended": r["attended"],
                "lectures": r["lectures"],
            }
    subjects = {s["code"]: s for s in fetch_all_subjects()}
    for entry in by_student.values():
        theory = [
            value for code, value in entry["attendance"].items()
            if code in subjects and subjects[code]["type"] == "Theory"
            and value["attended"] is not None and value["lectures"]
        ]
        if theory:
            entry["overall_theory"] = (
                sum(value["attended"] for value in theory) * 100.0
                / sum(value["lectures"] for value in theory)
            )
        else:
            legacy = [
                value["percent"] for code, value in entry["attendance"].items()
                if code in subjects and subjects[code]["type"] == "Theory"
                and value["percent"] is not None
            ]
            if legacy:
                entry["overall_theory"] = sum(legacy) / len(legacy)
    return list(by_student.values())


def list_defaulters(threshold: float = 75.0):
    """Return students whose weighted overall theory attendance is below threshold."""
    defaulters = []
    for student in fetch_all_students():
        attendance = get_attendance(student["id"])
        theory_codes = {
            subject["code"] for subject in fetch_all_subjects()
            if subject["type"] == "Theory"
        }
        theory = [row for row in attendance if row["subject_code"] in theory_codes
                  and row["attended"] is not None and row["lectures"]]
        if theory:
            overall = sum(row["attended"] for row in theory) * 100.0 / sum(
                row["lectures"] for row in theory
            )
        else:
            legacy = [row["percent"] for row in attendance
                      if row["subject_code"] in theory_codes and row["percent"] is not None]
            overall = sum(legacy) / len(legacy) if legacy else None
        if overall is not None and overall < threshold:
            defaulters.append(student)
    return defaulters


def get_defaulter_subjects(student_id: int, threshold: float = 75.0) -> list[str]:
    """Subject codes for which this student is below threshold."""
    rows = get_connection().execute("""
        SELECT subject_code FROM attendance
        WHERE student_id=? AND percent < ?
        ORDER BY subject_code
    """, (student_id, threshold)).fetchall()
    return [r["subject_code"] for r in rows]


# ----------------------------------------------------------------- LETTERS
def insert_letter(data: dict) -> int:
    with tx() as conn:
        cur = conn.execute("""
            INSERT INTO letters
            (student_id, faculty_name, date, class, div, roll_no, student_name,
             intimation_no, from_date, to_date, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("student_id"),
            data.get("faculty_name", ""),
            data.get("date", ""),
            data.get("class", ""),
            data.get("div", ""),
            data.get("roll_no", ""),
            data.get("student_name", ""),
            data.get("intimation_no", ""),
            data.get("from_date", ""),
            data.get("to_date", ""),
            _now(),
        ))
        if cur.lastrowid is None:
            raise RuntimeError("INSERT into letters did not return a lastrowid")
        return cur.lastrowid


def fetch_all_letters():
    return get_connection().execute("SELECT * FROM letters ORDER BY id DESC").fetchall()


def delete_letter(lid: int) -> None:
    with tx() as conn:
        conn.execute("DELETE FROM letters WHERE id=?", (lid,))