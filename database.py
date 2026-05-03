import sqlite3
from pathlib import Path

DB_PATH = Path("course_data.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_url TEXT NOT NULL,
        university_name TEXT,
        course_name TEXT,
        country TEXT,
        level TEXT,
        tuition_fee TEXT,
        currency TEXT,
        ielts_requirement TEXT,
        pte_requirement TEXT,
        toefl_requirement TEXT,
        duration TEXT,
        intake TEXT,
        application_fee TEXT,
        deposit TEXT,
        scholarship_info TEXT,
        entry_requirement_snippet TEXT,
        raw_confidence_json TEXT,
        raw_snippets_json TEXT,
        verified_status TEXT DEFAULT 'draft',
        last_checked TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

def insert_course(data):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO courses (
        source_url, university_name, course_name, country, level,
        tuition_fee, currency, ielts_requirement, pte_requirement, toefl_requirement,
        duration, intake, application_fee, deposit, scholarship_info,
        entry_requirement_snippet, raw_confidence_json, raw_snippets_json,
        verified_status, last_checked
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, DATE('now'))
    """, (
        data.get("source_url"),
        data.get("university_name"),
        data.get("course_name"),
        data.get("country"),
        data.get("level"),
        data.get("tuition_fee"),
        data.get("currency"),
        data.get("ielts_requirement"),
        data.get("pte_requirement"),
        data.get("toefl_requirement"),
        data.get("duration"),
        data.get("intake"),
        data.get("application_fee"),
        data.get("deposit"),
        data.get("scholarship_info"),
        data.get("entry_requirement_snippet"),
        data.get("raw_confidence_json"),
        data.get("raw_snippets_json"),
        data.get("verified_status", "draft"),
    ))

    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id

def list_courses():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM courses ORDER BY id DESC").fetchall()
    conn.close()
    return rows

def get_course(course_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
    conn.close()
    return row

def update_course(course_id, data):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    UPDATE courses SET
        university_name = ?,
        course_name = ?,
        country = ?,
        level = ?,
        tuition_fee = ?,
        currency = ?,
        ielts_requirement = ?,
        pte_requirement = ?,
        toefl_requirement = ?,
        duration = ?,
        intake = ?,
        application_fee = ?,
        deposit = ?,
        scholarship_info = ?,
        entry_requirement_snippet = ?,
        verified_status = ?,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (
        data.get("university_name"),
        data.get("course_name"),
        data.get("country"),
        data.get("level"),
        data.get("tuition_fee"),
        data.get("currency"),
        data.get("ielts_requirement"),
        data.get("pte_requirement"),
        data.get("toefl_requirement"),
        data.get("duration"),
        data.get("intake"),
        data.get("application_fee"),
        data.get("deposit"),
        data.get("scholarship_info"),
        data.get("entry_requirement_snippet"),
        data.get("verified_status"),
        course_id
    ))

    conn.commit()
    conn.close()

def delete_course(course_id):
    conn = get_connection()
    conn.execute("DELETE FROM courses WHERE id = ?", (course_id,))
    conn.commit()
    conn.close()
